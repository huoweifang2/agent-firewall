"""POST /agent/chat — agent chat endpoint."""

from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from src.agent.graph import get_agent_graph
from src.agent.openclaw_client import OpenClawClient, OpenClawError
from src.agent.rbac.service import get_rbac_service
from src.config import get_settings
from src.schemas import (
    AgentChatRequest,
    AgentChatResponse,
    AgentTrace,
    FirewallDecision,
    OpenClawDirectRequest,
    OpenClawDirectResponse,
)

logger = structlog.get_logger()
router = APIRouter(tags=["agent"])
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


def _validate_legacy_role(body: AgentChatRequest) -> None:
    if body.agent_id:
        return
    if get_rbac_service().get_role_config(body.user_role) is not None:
        return
    raise HTTPException(status_code=422, detail=f"Unknown user_role '{body.user_role}'")


def _firewall_decision(scan: dict) -> FirewallDecision:
    return FirewallDecision(
        decision=str(scan.get("decision", "UNKNOWN")),
        risk_score=float(scan.get("risk_score", 0.0) or 0.0),
        intent=str(scan.get("intent", "") or ""),
        risk_flags=scan.get("risk_flags") if isinstance(scan.get("risk_flags"), dict) else {},
        blocked_reason=scan.get("blocked_reason"),
    )


_NO_REPLY_VALUES = {"", "NO_REPLY", "null", "None"}
_NO_VISIBLE_REPLY = "OpenClaw completed the request without a visible reply."


def _clean_openclaw_text(text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip() not in _NO_REPLY_VALUES]
    cleaned = "\n".join(lines).strip()
    if not cleaned:
        return _NO_VISIBLE_REPLY
    if len(cleaned) > 2000 and "finalAssistantVisibleText" in cleaned and "NO_REPLY" in cleaned:
        return _NO_VISIBLE_REPLY
    return cleaned


def _first_text(value: Any, keys: tuple[str, ...]) -> str | None:
    if not isinstance(value, dict):
        return None
    for key in keys:
        text = value.get(key)
        if isinstance(text, str) and text.strip() not in _NO_REPLY_VALUES:
            return text.strip()
    return None


def _extract_openclaw_response(payload: object) -> str:
    if isinstance(payload, dict):
        direct = _first_text(payload, ("response", "reply", "message", "content", "text", "result", "output"))
        if direct:
            return direct

        result = payload.get("result")
        if isinstance(result, dict):
            nested = _first_text(result, ("response", "reply", "message", "content", "text", "output"))
            if nested:
                return _clean_openclaw_text(nested)
            meta = result.get("meta")
            meta_text = (
                _first_text(meta, ("finalAssistantVisibleText", "finalAssistantRawText"))
                if isinstance(meta, dict)
                else None
            )
            if meta_text:
                return _clean_openclaw_text(meta_text)
            summary = result.get("summary") or payload.get("summary")
            if isinstance(summary, str) and summary.strip():
                return f"OpenClaw completed: {summary.strip()}"

        meta = payload.get("meta")
        meta_text = (
            _first_text(meta, ("finalAssistantVisibleText", "finalAssistantRawText"))
            if isinstance(meta, dict)
            else None
        )
        if meta_text:
            return _clean_openclaw_text(meta_text)

        return _NO_VISIBLE_REPLY
    return _clean_openclaw_text(str(payload))


def _resolve_openclaw_agent_id(request_agent_id: str | None) -> str:
    """Treat control-plane UUIDs as registry IDs, not OpenClaw agent IDs."""
    settings = get_settings()
    if not request_agent_id or _UUID_RE.match(request_agent_id):
        return settings.openclaw_agent_id
    return request_agent_id


def _build_openclaw_response(
    *,
    body: AgentChatRequest,
    response: str,
    scan: dict,
    started_at: float,
    agent_id: str,
    trace: dict,
) -> AgentChatResponse:
    return AgentChatResponse(
        session_id=body.session_id,
        response=response,
        tools_called=[],
        agent_trace=AgentTrace(
            agent_id=agent_id,
            agent_name="OpenClaw",
            agent_kind="openclaw",
            tool_flow=trace.get("tool_flow", []),
            intent=str(scan.get("intent", "unknown") or "unknown"),
            user_role=body.user_role,
            allowed_tools=["openclaw.agent"],
            iterations=1,
            latency_ms=int((time.perf_counter() - started_at) * 1000),
        ),
        firewall_decision=_firewall_decision(scan),
        trace=trace,
    )


def _preview(value: object, max_len: int = 500) -> str:
    text = str(value or "")
    return text[:max_len]


def _state_to_chat_response(body: AgentChatRequest, state: dict) -> AgentChatResponse:
    trace = state.get("trace") if isinstance(state.get("trace"), dict) else {}
    tool_calls = []
    for call in state.get("tool_calls", []) or []:
        if not isinstance(call, dict):
            continue
        result = call.get("sanitized_result") or call.get("result") or ""
        blocked_reason = None
        if not call.get("allowed", True):
            blocked_reason = str(call.get("result") or "")
        post_gate = call.get("post_gate")
        if isinstance(post_gate, dict) and post_gate.get("decision") == "BLOCK":
            blocked_reason = str(post_gate.get("reason") or "Blocked by post-tool gate.")
        tool_calls.append(
            {
                "tool": str(call.get("tool", "")),
                "args": call.get("args") if isinstance(call.get("args"), dict) else {},
                "result_preview": _preview(result),
                "allowed": bool(call.get("allowed", True)) and blocked_reason is None,
                "blocked_reason": blocked_reason,
            }
        )

    firewall = state.get("firewall_decision") if isinstance(state.get("firewall_decision"), dict) else {}
    return AgentChatResponse(
        session_id=body.session_id,
        response=str(state.get("final_response") or state.get("llm_response") or ""),
        tools_called=tool_calls,
        agent_trace=AgentTrace(
            agent_id=str(state.get("agent_id") or ""),
            agent_name=str(state.get("agent_name") or trace.get("agent_name") or "Telegram OpenClaw Gateway"),
            agent_kind=str(trace.get("agent_kind") or "openclaw"),
            parent_agent_id=state.get("parent_agent_id"),
            delegated_from=state.get("delegated_from"),
            delegated_to=trace.get("delegated_to"),
            task=state.get("delegated_task"),
            tool_flow=trace.get("tool_flow", []) if isinstance(trace.get("tool_flow"), list) else [],
            intent=str(state.get("intent") or firewall.get("intent") or "unknown"),
            user_role=str(state.get("user_role") or body.user_role),
            allowed_tools=list(state.get("allowed_tools", [])),
            available_sub_agents=[
                str(item.get("name", ""))
                for item in state.get("available_sub_agents", [])
                if isinstance(item, dict) and item.get("name")
            ],
            iterations=int(state.get("iterations", 0) or 0),
            latency_ms=int(trace.get("total_duration_ms", 0) or 0),
        ),
        firewall_decision=_firewall_decision(firewall),
        trace=trace,
        pending_confirmation=state.get("pending_confirmation")
        if isinstance(state.get("pending_confirmation"), dict)
        else None,
    )


async def _scan_via_proxy(
    *,
    body: AgentChatRequest,
    policy: str,
    model: str,
    api_key: str | None,
    x_middlewares: str | None,
) -> dict:
    settings = get_settings()
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "x-client-id": f"agent-openclaw-{body.session_id}",
        "x-policy": policy,
        "x-correlation-id": body.session_id,
    }
    if api_key:
        headers["x-api-key"] = api_key
    if x_middlewares:
        headers["x-middlewares"] = x_middlewares

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.proxy_base_url.rstrip('/')}/scan",
            headers=headers,
            json={
                "model": model,
                "messages": [{"role": "user", "content": body.message}],
                "temperature": settings.default_temperature,
                "max_tokens": settings.default_max_tokens,
                "stream": False,
            },
        )

    data = resp.json()
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="Proxy scan returned an unexpected response.")
    data["status_code"] = resp.status_code
    if resp.status_code not in (200, 403):
        raise HTTPException(status_code=502, detail=f"Proxy scan failed with status {resp.status_code}.")
    return data


async def _run_openclaw_protected(
    *,
    body: AgentChatRequest,
    x_api_key: str | None,
    x_middlewares: str | None,
) -> AgentChatResponse:
    """Run the OpenClaw-only protected agent path."""
    settings = get_settings()
    started_at = time.perf_counter()
    policy = body.policy or settings.default_policy
    model = body.model or settings.default_model
    agent_id = _resolve_openclaw_agent_id(body.agent_id)
    trace: dict = {
        "runtime": "openclaw",
        "session_id": body.session_id,
        "policy": policy,
        "model": model,
        "tool_flow": [],
    }

    scan = await _scan_via_proxy(
        body=body,
        policy=policy,
        model=model,
        api_key=x_api_key,
        x_middlewares=x_middlewares,
    )
    trace["tool_flow"].append(
        {
            "stage": "input_scan",
            "decision": scan.get("decision"),
            "risk_score": scan.get("risk_score"),
            "intent": scan.get("intent"),
        }
    )

    if scan.get("decision") == "BLOCK":
        reason = scan.get("blocked_reason") or "Request blocked by security policy."
        return _build_openclaw_response(
            body=body,
            response=f"Request blocked by Agent-Firewall: {reason}",
            scan=scan,
            started_at=started_at,
            agent_id=agent_id,
            trace=trace,
        )

    client = OpenClawClient(
        binary=settings.openclaw_bin,
        timeout_seconds=settings.openclaw_timeout_seconds,
        default_agent_id=agent_id,
        local=settings.openclaw_agent_local,
        plugin_stage_dir=settings.openclaw_plugin_stage_dir,
    )
    try:
        payload = await client.agent_message(
            message=body.message,
            session_id=body.session_id,
            agent_id=agent_id,
            timeout_seconds=settings.openclaw_timeout_seconds,
        )
    except OpenClawError as exc:
        trace["tool_flow"].append({"stage": "openclaw_agent", "status": "error"})
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    response = _extract_openclaw_response(payload)
    trace["tool_flow"].append({"stage": "openclaw_agent", "status": "ok", "agent_id": agent_id})
    return _build_openclaw_response(
        body=body,
        response=response,
        scan=scan,
        started_at=started_at,
        agent_id=agent_id,
        trace=trace,
    )


@router.post("/agent/chat")
async def agent_chat(
    body: AgentChatRequest,
    x_api_key: str | None = Header(default=None),
    x_middlewares: str | None = Header(default=None),
    accept: str | None = Header(default=None),
):
    """Run the protected Agent-Firewall runtime graph."""
    _validate_legacy_role(body)
    wants_sse = bool(accept and "text/event-stream" in accept.lower())
    graph = get_agent_graph()

    async def run_graph() -> AgentChatResponse:
        state = await graph.ainvoke(
            {
                "message": body.message,
                "user_role": body.user_role,
                "session_id": body.session_id,
                "agent_id": body.agent_id,
                "policy": body.policy,
                "model": body.model,
                "api_key": x_api_key,
                "x_middlewares": x_middlewares,
                "approved_intervention_id": body.approved_intervention_id,
            }
        )
        return _state_to_chat_response(body, state)

    if not wants_sse:
        return await run_graph()

    async def event_generator():
        response_obj = await run_graph()
        if response_obj.response:
            yield f"event: chunk\ndata: {json.dumps({'content': response_obj.response})}\n\n"
        yield f"event: final\ndata: {response_obj.model_dump_json()}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/agent/openclaw/direct", response_model=OpenClawDirectResponse)
async def openclaw_direct(body: OpenClawDirectRequest) -> OpenClawDirectResponse:
    """Call OpenClaw directly for Compare's unprotected side.

    This intentionally bypasses Agent-Firewall scan and tool gates so the UI can
    compare raw OpenClaw behavior against the protected `/agent/chat` path.
    """
    settings = get_settings()
    agent_id = _resolve_openclaw_agent_id(body.agent_id)
    client = OpenClawClient(
        binary=settings.openclaw_bin,
        timeout_seconds=settings.openclaw_timeout_seconds,
        default_agent_id=agent_id,
        local=settings.openclaw_agent_local,
        plugin_stage_dir=settings.openclaw_plugin_stage_dir,
    )

    started_at = time.perf_counter()
    try:
        payload = await client.agent_message(
            message=body.message,
            session_id=body.session_id,
            agent_id=agent_id,
            timeout_seconds=body.timeout_seconds,
        )
    except OpenClawError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    response = _extract_openclaw_response(payload)

    return OpenClawDirectResponse(
        session_id=body.session_id,
        response=response,
        agent_id=agent_id,
        latency_ms=int((time.perf_counter() - started_at) * 1000),
    )
