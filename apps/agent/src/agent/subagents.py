"""Sub-agent delegation runtime."""

from __future__ import annotations

from uuid import uuid4

import httpx

from src.agent.runtime_access import resolve_effective_role
from src.agent.runtime_loader import clear_runtime_cache, load_runtime_spec
from src.config import get_settings


async def run_sub_agent(
    *,
    parent_state: dict,
    child_agent_id: str,
    task: str,
) -> str:
    settings = get_settings()
    parent_depth = int(parent_state.get("delegation_depth", 0))
    max_depth = int(parent_state.get("max_delegation_depth", 2))
    if parent_depth >= max_depth:
        return "Delegation depth limit reached."

    child_spec = await load_runtime_spec(child_agent_id, settings)
    if child_spec is None:
        return f"Unable to load sub-agent runtime spec for {child_agent_id}."

    child_role = resolve_effective_role(parent_state.get("user_role"), child_spec)
    from src.agent.graph import get_agent_graph

    child_state = {
        "agent_id": child_agent_id,
        "parent_agent_id": parent_state.get("agent_id"),
        "delegated_from": parent_state.get("agent_name") or parent_state.get("agent_id"),
        "delegated_task": task,
        "session_id": f"{parent_state.get('session_id', 'session')}::sub::{uuid4().hex[:8]}",
        "user_role": child_role,
        "message": task,
        "policy": parent_state.get("policy"),
        "model": parent_state.get("model"),
        "api_key": parent_state.get("api_key"),
        "delegation_depth": parent_depth + 1,
        "max_delegation_depth": max_depth,
    }
    result = await get_agent_graph().ainvoke(child_state)
    return str(result.get("final_response") or result.get("llm_response") or "")


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
