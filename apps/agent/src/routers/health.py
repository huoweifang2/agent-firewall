"""System and OpenClaw runtime diagnostics."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from src.agent.openclaw_client import OpenClawClient, OpenClawError
from src.config import get_settings
from src.schemas import OpenClawRuntimeDiagnostics

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {"status": "ok", "version": settings.app_version}


def _read_openclaw_config() -> dict:
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _telegram_summary(openclaw_config: dict) -> tuple[bool, int]:
    channel = openclaw_config.get("channels", {}).get("telegram", {})
    if not isinstance(channel, dict):
        return False, 0

    accounts = channel.get("accounts")
    account_count = len(accounts) if isinstance(accounts, dict) else 0
    enabled = bool(channel.get("enabled", False))
    return enabled, account_count


def _gateway_summary(openclaw_config: dict) -> tuple[str, bool]:
    gateway = openclaw_config.get("gateway", {})
    if not isinstance(gateway, dict):
        return "unknown", False

    auth = gateway.get("auth", {})
    token_present = isinstance(auth, dict) and bool(auth.get("token"))
    mode = gateway.get("mode")
    return str(mode or "unknown"), token_present


def _diagnostic_client() -> OpenClawClient:
    settings = get_settings()
    return OpenClawClient(
        binary=settings.openclaw_bin,
        timeout_seconds=min(settings.openclaw_timeout_seconds, 20),
        default_agent_id=settings.openclaw_agent_id,
        local=settings.openclaw_agent_local,
    )


@router.get("/agent/openclaw/config", response_model=OpenClawRuntimeDiagnostics)
async def openclaw_config() -> OpenClawRuntimeDiagnostics:
    settings = get_settings()
    openclaw_config = _read_openclaw_config()
    telegram_enabled, telegram_accounts = _telegram_summary(openclaw_config)
    gateway_mode, gateway_token_present = _gateway_summary(openclaw_config)

    diagnostics = OpenClawRuntimeDiagnostics(
        openclaw_bin=settings.openclaw_bin,
        openclaw_agent_id=settings.openclaw_agent_id,
        openclaw_agent_local=settings.openclaw_agent_local,
        openclaw_timeout_seconds=settings.openclaw_timeout_seconds,
        deepseek_configured=bool(settings.deepseek_api_key),
        default_model=settings.default_model,
        default_model_prefix=settings.default_model_prefix,
        telegram_enabled=telegram_enabled,
        telegram_accounts=telegram_accounts,
        gateway_mode=gateway_mode,
        gateway_token_present=gateway_token_present,
    )

    client = _diagnostic_client()
    errors: list[str] = []

    for field, call in (
        ("status_ok", client.status),
        ("models_ok", client.models_status),
        ("agents_ok", client.list_agents),
    ):
        try:
            await call()
            setattr(diagnostics, field, True)
        except OpenClawError as exc:
            errors.append(f"{field}: {exc}")

    if errors:
        diagnostics.error = " | ".join(errors)
    return diagnostics
