"""POST /agent/chat — agent chat endpoint."""

from __future__ import annotations

import json
import time

import structlog
from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse

from src.agent.graph import get_agent_graph
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


@router.post("/agent/chat")
async def agent_chat(
    body: AgentChatRequest,
    x_api_key: str | None = Header(default=None),
    x_middlewares: str | None = Header(default=None),
):
    """Stream the agent graph execution."""
    settings = get_settings()

    # Build initial state
    initial_state = {
        "session_id": body.session_id,
        "user_role": body.user_role,
        "message": body.message,
        "policy": body.policy or settings.default_policy,
        "model": body.model or settings.default_model,
        "api_key": x_api_key,
        "x_middlewares": x_middlewares,
    }

    graph = get_agent_graph()

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

                response_obj = AgentChatResponse(
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
                        intent=final_state.get("intent", "unknown"),
                        user_role=final_state.get("user_role", "customer"),
                        allowed_tools=final_state.get("allowed_tools", []),
                        iterations=final_state.get("iterations", 0),
                        latency_ms=int((time.perf_counter() - start) * 1000),
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
                yield f"event: final\ndata: {response_obj.model_dump_json()}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
