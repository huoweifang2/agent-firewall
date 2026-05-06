"""Sub-agent delegation runtime."""

from __future__ import annotations

import json
from uuid import uuid4

import httpx

from src.agent.openclaw_client import OpenClawClient, OpenClawError, derive_session_id
from src.agent.runtime_loader import clear_runtime_cache
from src.agent.tools.providers.openclaw import _extract_result
from src.config import get_settings


async def run_sub_agent(
    *,
    parent_state: dict,
    sub_agent: dict,
    task: str,
) -> str:
    settings = get_settings()
    parent_depth = int(parent_state.get("delegation_depth", 0))
    max_depth = int(parent_state.get("max_delegation_depth", 2))
    if parent_depth >= max_depth:
        return "Delegation depth limit reached."

    openclaw_agent_id = str(sub_agent.get("openclaw_agent_id") or sub_agent.get("agent_id") or "").strip()
    if not openclaw_agent_id:
        return f"Unable to delegate to {sub_agent.get('name', 'sub-agent')}: no OpenClaw agent id is configured."

    session_seed = f"{parent_state.get('session_id', 'session')}::sub::{uuid4().hex[:8]}"
    prompt = (
        "You are running as an OpenClaw sub-agent delegated by Agent-Firewall.\n"
        f"Parent agent: {parent_state.get('agent_name') or parent_state.get('agent_id') or 'unknown'}\n"
        f"Sub-agent: {sub_agent.get('name', openclaw_agent_id)}\n"
        f"Delegation guidance: {sub_agent.get('delegation_description') or sub_agent.get('when_to_delegate') or ''}\n\n"
        f"Task:\n{task}\n\n"
        "Return the concise result needed by the parent agent. Do not include hidden reasoning."
    )
    client = OpenClawClient(
        binary=settings.openclaw_bin,
        timeout_seconds=settings.openclaw_timeout_seconds,
        default_agent_id=openclaw_agent_id,
        local=settings.openclaw_agent_local,
        plugin_stage_dir=settings.openclaw_plugin_stage_dir,
    )
    try:
        payload = await client.agent_message(
            agent_id=openclaw_agent_id,
            session_id=derive_session_id(session_seed, f"delegate:{openclaw_agent_id}"),
            message=prompt,
        )
    except OpenClawError as exc:
        return f"Error delegating to OpenClaw sub-agent {openclaw_agent_id}: {exc}"

    return _extract_result(payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False))


async def create_sub_agent_from_runtime(
    *,
    parent_state: dict,
    name: str,
    description: str = "",
    when_to_delegate: str = "",
    delegation_description: str = "",
) -> str:
    """Create a subagent through proxy-service and refresh the parent runtime cache."""
    parent_agent_id = str(parent_state.get("agent_id") or "")
    if not parent_agent_id:
        return "Unable to create subagent: no main agent is selected."

    settings = get_settings()
    url = f"{settings.proxy_base_url.rstrip('/')}/agents/{parent_agent_id}/sub-agents/create"
    payload = {
        "name": name,
        "description": description,
        "when_to_delegate": when_to_delegate,
        "delegation_description": delegation_description,
        "template_key": "sandbox_chat",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(url, json=payload)
    if resp.status_code not in (200, 201):
        return f"Unable to create subagent: {resp.status_code} {resp.text[:200]}"

    data = resp.json()
    clear_runtime_cache(parent_agent_id)
    clear_runtime_cache(str(data.get("child_agent_id", "")))
    child_name = data.get("child_agent_name") or name
    return (
        f"Created subagent '{child_name}' and added it to this main agent. "
        f"Delegate to it when: {data.get('when_to_delegate') or when_to_delegate or 'its specialization matches the task'}."
    )
