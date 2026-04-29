"""InputNode — validate input, sanitize user message and load session history."""

from __future__ import annotations

import structlog

from src.agent.limits.service import get_limits_service
from src.agent.runtime_access import get_runtime_skills, get_runtime_sub_agents, resolve_effective_role
from src.agent.runtime_loader import load_runtime_spec
from src.agent.security.sanitizer import sanitize_user_input
from src.agent.state import AgentState
from src.agent.trace.accumulator import TraceAccumulator
from src.config import get_settings
from src.session import session_store

logger = structlog.get_logger()


async def input_node(state: AgentState) -> AgentState:
    """Load session history, sanitize user input, check limits and initialize state."""
    session_id = state["session_id"]
    chat_history = session_store.get_history(session_id)
    settings = get_settings()
    runtime_spec = await load_runtime_spec(state.get("agent_id"), settings)
    effective_role = resolve_effective_role(state.get("user_role"), runtime_spec)

    # Sanitize user message at the earliest point (spec 05)
    raw_message = state.get("message", "")
    sanitized_message = sanitize_user_input(raw_message)

    # ── Limit checks at request entry (spec 06) ──────────
    limits_svc = get_limits_service()
    limit_check = limits_svc.check_request_entry(
        session_id=session_id,
        user_id=session_id,  # user_id ≈ session_id for now
        role=effective_role,
    )

    usage = limits_svc.get_session_usage(session_id)

    logger.info(
        "input_node",
        session_id=session_id,
        history_len=len(chat_history),
        message_sanitized=raw_message != sanitized_message,
        limit_ok=limit_check.allowed,
    )

    # ── Trace init (spec 07) ────────────────────────────
    trace = TraceAccumulator()
    trace.start(
        session_id=session_id,
        agent_id=str(state.get("agent_id") or settings.agent_id or ""),
        agent_name=runtime_spec.get("name", "") if runtime_spec else "",
        agent_kind=runtime_spec.get("agent_kind", "") if runtime_spec else "",
        parent_agent_id=state.get("parent_agent_id"),
        delegated_from=state.get("delegated_from"),
        task=state.get("delegated_task"),
        user_role=effective_role,
        policy=state.get("policy", ""),
        model=state.get("model", ""),
        user_message=sanitized_message,
    )

    base_state: dict = {
        **state,
        "agent_id": state.get("agent_id") or settings.agent_id or "",
        "agent_name": runtime_spec.get("name", "") if runtime_spec else "",
        "runtime_spec": runtime_spec,
        "skills": get_runtime_skills(runtime_spec),
        "available_sub_agents": get_runtime_sub_agents(runtime_spec),
        "user_role": effective_role,
        "message": sanitized_message,
        "chat_history": chat_history,
        "tool_calls": state.get("tool_calls", []),
        "tool_plan": [],
        "iterations": 0,
        "errors": state.get("errors", []),
        "node_timings": state.get("node_timings", {}),
        # Limits counters (spec 06)
        "session_tool_calls": usage["session_tool_calls"],
        "session_tokens_in": usage["session_tokens_in"],
        "session_tokens_out": usage["session_tokens_out"],
        "session_estimated_cost": usage["session_estimated_cost"],
        "session_turns": usage["session_turns"],
        "limit_exceeded": None,
        "delegation_depth": int(state.get("delegation_depth", 0)),
        "max_delegation_depth": int(state.get("max_delegation_depth", 2)),
        # Trace (spec 07)
        "trace": trace.data,
    }

    if not limit_check.allowed:
        base_state["limit_exceeded"] = limit_check.limit_type
        base_state["final_response"] = limit_check.message
        trace.record_limit_hit(limit_check.limit_type or "unknown")

    return base_state
