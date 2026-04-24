"""Sub-agent delegation runtime."""

from __future__ import annotations

from uuid import uuid4

from src.agent.runtime_access import resolve_effective_role
from src.agent.runtime_loader import load_runtime_spec
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
