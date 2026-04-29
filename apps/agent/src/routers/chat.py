"""POST /agent/chat — agent chat endpoint."""

from __future__ import annotations

import json
import time

import structlog
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from src.agent.graph import get_agent_graph
from src.agent.rbac.service import get_rbac_service
from src.config import get_settings
from src.schemas import (
    AgentChatRequest,
    AgentChatResponse,
    AgentTrace,
    FirewallDecision,
    ToolCallInfo,
)

logger = structlog.get_logger()
router = APIRouter(tags=["agent"])


def _validate_legacy_role(body: AgentChatRequest) -> None:
    if body.agent_id:
        return
    if get_rbac_service().get_role_config(body.user_role) is not None:
        return
    raise HTTPException(status_code=422, detail=f"Unknown user_role '{body.user_role}'")


def _build_response_obj(final_state: dict, started_at: float) -> AgentChatResponse:
    return AgentChatResponse(
        session_id=final_state.get("session_id", ""),
        response=final_state.get("final_response", ""),
        tools_called=[
            ToolCallInfo(
                tool=t.get("tool", ""),
                args=t.get("args", {}),
                result_preview=str(t.get("result", "")),
                allowed=t.get("allowed", True),
                blocked_reason=t.get("post_gate", {}).get("reason") if t.get("post_gate") else None,
            )
            for t in final_state.get("tool_calls", [])
        ],
        agent_trace=AgentTrace(
            agent_id=str(final_state.get("agent_id", "")),
            agent_name=final_state.get("agent_name", ""),
            agent_kind=(final_state.get("runtime_spec") or {}).get("agent_kind", ""),
            parent_agent_id=final_state.get("parent_agent_id"),
            delegated_from=final_state.get("delegated_from"),
            delegated_to=(final_state.get("trace") or {}).get("delegated_to"),
            task=final_state.get("delegated_task"),
            tool_flow=(final_state.get("trace") or {}).get("tool_flow", []),
            intent=final_state.get("intent", "unknown"),
            user_role=final_state.get("user_role", "customer"),
            allowed_tools=final_state.get("allowed_tools", []),
            available_sub_agents=[sa.get("name", "") for sa in final_state.get("available_sub_agents", [])],
            iterations=final_state.get("iterations", 0),
            latency_ms=int((time.perf_counter() - started_at) * 1000),
        ),
        firewall_decision=FirewallDecision(
            decision=final_state.get("firewall_decision", {}).get("decision", "UNKNOWN")
            if final_state.get("firewall_decision")
            else "UNKNOWN",
            risk_score=final_state.get("firewall_decision", {}).get("risk_score", 0.0)
            if final_state.get("firewall_decision")
            else 0.0,
            intent=final_state.get("firewall_decision", {}).get("intent", "")
            if final_state.get("firewall_decision")
            else "",
            risk_flags=final_state.get("firewall_decision", {}).get("risk_flags", {})
            if final_state.get("firewall_decision")
            else {},
            blocked_reason=final_state.get("firewall_decision", {}).get("blocked_reason")
            if final_state.get("firewall_decision")
            else None,
        ),
        trace=final_state.get("trace", {}),
    )


@router.post("/agent/chat")
async def agent_chat(
    body: AgentChatRequest,
    x_api_key: str | None = Header(default=None),
    x_middlewares: str | None = Header(default=None),
    accept: str | None = Header(default=None),
):
    """Stream the agent graph execution."""
    settings = get_settings()
    _validate_legacy_role(body)

    # Build initial state
    initial_state = {
        "agent_id": body.agent_id,
        "session_id": body.session_id,
        "user_role": body.user_role,
        "message": body.message,
        "policy": body.policy or settings.default_policy,
        "model": body.model or settings.default_model,
        "api_key": x_api_key,
        "x_middlewares": x_middlewares,
    }

    graph = get_agent_graph()
    wants_sse = bool(accept and "text/event-stream" in accept.lower())

    if not wants_sse:
        start = time.perf_counter()
        final_state = await graph.ainvoke(initial_state)
        return _build_response_obj(final_state, start)

    async def event_generator():
        start = time.perf_counter()

        async for event in graph.astream_events(initial_state, version="v2"):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    yield f"event: chunk\ndata: {json.dumps({'content': chunk.content})}\n\n"

            elif kind == "on_tool_start":
                kwargs = event["data"].get("input")
                yield f"event: tool_start\ndata: {json.dumps({'name': event['name'], 'kwargs': kwargs})}\n\n"

            elif kind == "on_tool_end":
                output = event["data"].get("output", {})
                if isinstance(output, dict):
                    result = output.get("result", "")
                    allowed = output.get("allowed", True)
                else:
                    result = str(output)
                    allowed = True
                yield f"event: tool_end\ndata: {json.dumps({'result': result, 'allowed': allowed})}\n\n"

            elif kind == "on_chain_end" and event["name"] == "LangGraph":
                final_state = event["data"]["output"]
                response_obj = _build_response_obj(final_state, start)
                yield f"event: final\ndata: {response_obj.model_dump_json()}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
