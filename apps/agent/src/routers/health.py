"""GET /health — readiness check."""

from __future__ import annotations

from fastapi import APIRouter

from src.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {"status": "ok", "version": settings.app_version}


@router.get("/agent/openclaw/config")
async def openclaw_config() -> dict:
    settings = get_settings()
    return {
        "openclaw_bin": settings.openclaw_bin,
        "openclaw_agent_id": settings.openclaw_agent_id,
        "openclaw_agent_local": settings.openclaw_agent_local,
        "openclaw_timeout_seconds": settings.openclaw_timeout_seconds,
    }
