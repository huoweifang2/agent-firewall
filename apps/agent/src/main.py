"""Agent-Firewall Agent — protected external OpenClaw runtime."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.agent.telegram_bridge import start_telegram_bridge, stop_telegram_bridge
from src.config import get_settings
from src.routers.chat import router as chat_router
from src.routers.health import router as health_router
from src.routers.traces import router as traces_router

logger = structlog.get_logger()

_AGENT_NAME = "Telegram OpenClaw Gateway"
_AGENT_PAYLOAD = {
    "name": _AGENT_NAME,
    "description": "Telegram OpenClaw agent protected by Agent-Firewall scans, tool gates, approvals, and traces.",
    "team": "personal",
    "framework": "openclaw",
    "environment": "production",
    "is_public_facing": True,
    "has_tools": True,
    "has_write_actions": True,
    "touches_pii": True,
    "handles_secrets": True,
    "calls_external_apis": True,
    "policy_pack": "telegram_gateway",
    "agent_kind": "main_agent",
    "created_from": "template",
    "template_key": "telegram_openclaw_gateway",
}


async def _ensure_agent_registered(settings) -> None:
    """Register the agent with the proxy-service control plane if no agent_id is set.

    Tries to find an existing agent by name first; creates one if not found.
    Updates settings.agent_id in-place so memory_node picks it up immediately.
    """
    if settings.agent_id:
        logger.info("agent_id_already_set", agent_id=settings.agent_id)
        return

    # proxy_base_url is like http://proxy-service:8000/v1; strip /v1 for control-plane API.
    base = settings.proxy_base_url.rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    control_plane_base = base + "/v1"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Search for existing agent by name
            resp = await client.get(
                f"{control_plane_base}/agents",
                params={"search": _AGENT_NAME, "per_page": 5},
            )
            if resp.status_code == 200:
                for item in resp.json().get("items", []):
                    if item.get("name") == _AGENT_NAME:
                        settings.agent_id = item["id"]
                        if item.get("framework") != "openclaw":
                            await client.patch(
                                f"{control_plane_base}/agents/{settings.agent_id}",
                                json={"framework": "openclaw"},
                            )
                        logger.info(
                            "agent_found_in_control_plane",
                            agent_id=settings.agent_id,
                        )
                        return

            # 2. Not found — register
            resp = await client.post(f"{control_plane_base}/agents", json=_AGENT_PAYLOAD)
            if resp.status_code == 201:
                settings.agent_id = resp.json()["id"]
                logger.info(
                    "agent_registered",
                    agent_id=settings.agent_id,
                )
            elif resp.status_code == 409:
                # Race condition — search again
                resp2 = await client.get(
                    f"{control_plane_base}/agents",
                    params={"search": _AGENT_NAME, "per_page": 5},
                )
                if resp2.status_code == 200:
                    for item in resp2.json().get("items", []):
                        if item.get("name") == _AGENT_NAME:
                            settings.agent_id = item["id"]
                            logger.info(
                                "agent_registered_race",
                                agent_id=settings.agent_id,
                            )
                            return
            else:
                logger.warning(
                    "agent_registration_failed",
                    status=resp.status_code,
                    body=resp.text[:300],
                )
    except Exception as exc:
        logger.warning("agent_registration_error", error=str(exc)[:300])


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle."""
    settings = get_settings()

    # Silence verbose LiteLLM logs
    os.environ["LITELLM_LOG"] = settings.litellm_log_level

    logger.info("agent_starting", version=settings.app_version)

    # Auto-register with proxy-service control plane so traces are forwarded.
    await _ensure_agent_registered(settings)
    await start_telegram_bridge(settings)

    logger.info(
        "agent_ready",
        proxy_url=settings.proxy_base_url,
        model=settings.default_model,
        agent_id=settings.agent_id or "unregistered",
    )
    yield
    await stop_telegram_bridge()
    logger.info("agent_stopped")


settings = get_settings()

app = FastAPI(
    title="Agent-Firewall — Agent",
    description="Protected external OpenClaw runtime behind the Agent-Firewall firewall",
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "x-client-id", "x-api-key", "x-correlation-id", "x-middlewares", "x-policy"],
)

# Routers
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(traces_router)
