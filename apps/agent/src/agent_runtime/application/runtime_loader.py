"""Load runtime specs for agent execution from proxy-service."""

from __future__ import annotations

import time
from typing import Any

import httpx

from agent_runtime.infrastructure.config import Settings

_CACHE_TTL_SECONDS = 15.0
_runtime_cache: dict[str, tuple[float, dict[str, Any]]] = {}


async def load_runtime_spec(agent_id: str | None, settings: Settings) -> dict[str, Any] | None:
    """Fetch an agent runtime spec by id, with a short in-process cache."""
    effective_id = agent_id or settings.agent_id or ""
    if not effective_id:
        return None

    cached = _runtime_cache.get(effective_id)
    now = time.monotonic()
    if cached and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    url = f"{settings.proxy_base_url.rstrip('/')}/agents/{effective_id}/runtime-spec"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url)
    resp.raise_for_status()
    data = resp.json()
    _runtime_cache[effective_id] = (now, data)
    return data


def clear_runtime_cache(agent_id: str | None = None) -> None:
    """Clear the runtime cache for one agent or all agents."""
    if agent_id is None:
        _runtime_cache.clear()
        return
    _runtime_cache.pop(agent_id, None)
