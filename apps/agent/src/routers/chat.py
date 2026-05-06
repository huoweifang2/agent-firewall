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
            meta_text = _first_text(meta, ("finalAssistantVisibleText", "finalAssistantRawText")) if isinstance(meta, dict) else None
            if meta_text:
                return _clean_openclaw_text(meta_text)
            summary = result.get("summary") or payload.get("summary")
            if isinstance(summary, str) and summary.strip():
                return f"OpenClaw completed: {summary.strip()}"

        meta = payload.get("meta")
        meta_text = _first_text(meta, ("finalAssistantVisibleText", "finalAssistantRawText")) if isinstance(meta, dict) else None
        if meta_text:
            return _clean_openclaw_text(meta_text)

        return _NO_VISIBLE_REPLY
    return _clean_openclaw_text(str(payload))


def _resolve_openclaw_agent_id(request_agent_id: str | None) -> str:
    """Treat wizard UUIDs as control-plane IDs, not OpenClaw agent IDs."""
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
    """Run Agent-Firewall scan, then call OpenClaw as the only agent runtime."""
    _validate_legacy_role(body)
    wants_sse = bool(accept and "text/event-stream" in accept.lower())

    if not wants_sse:
        return await _run_openclaw_protected(body=body, x_api_key=x_api_key, x_middlewares=x_middlewares)

    async def event_generator():
        response_obj = await _run_openclaw_protected(body=body, x_api_key=x_api_key, x_middlewares=x_middlewares)
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
