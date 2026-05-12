"""Client helpers for the proxy-service intervention queue."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from agent_runtime.infrastructure.config import Settings, get_settings

logger = structlog.get_logger()


def _base_url(settings: Settings) -> str:
    return settings.proxy_base_url.rstrip("/")


async def create_intervention(payload: dict[str, Any], settings: Settings | None = None) -> dict[str, Any] | None:
    settings = settings or get_settings()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{_base_url(settings)}/interventions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else None
    except Exception as exc:
        logger.warning("intervention_create_failed", error=str(exc)[:300])
        return None


async def list_interventions(
    *,
    status: str,
    source: str = "telegram",
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    settings = settings or get_settings()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{_base_url(settings)}/interventions",
                params={"status": status, "source": source, "limit": 100},
            )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items") if isinstance(data, dict) else None
        return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []
    except Exception as exc:
        logger.warning("intervention_list_failed", status=status, error=str(exc)[:300])
        return []


async def get_intervention(intervention_id: str, settings: Settings | None = None) -> dict[str, Any] | None:
    settings = settings or get_settings()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{_base_url(settings)}/interventions/{intervention_id}")
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else None
    except Exception as exc:
        logger.warning("intervention_get_failed", intervention_id=intervention_id, error=str(exc)[:300])
        return None


async def update_intervention(
    intervention_id: str,
    payload: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any] | None:
    settings = settings or get_settings()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(f"{_base_url(settings)}/interventions/{intervention_id}", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else None
    except Exception as exc:
        logger.warning("intervention_update_failed", intervention_id=intervention_id, error=str(exc)[:300])
        return None
