"""OpenClaw-backed tool provider."""

from __future__ import annotations

import json
from typing import Any

from agent_runtime.infrastructure.config import get_settings
from agent_runtime.infrastructure.openclaw_client import OpenClawClient, OpenClawError, derive_session_id


def _get_openclaw_skill(tool_name: str, tool_spec: dict[str, Any] | None) -> str:
    provider = None
    arg_schema = tool_spec.get("arg_schema") if isinstance(tool_spec, dict) else None
    if isinstance(arg_schema, dict):
        provider = arg_schema.get("provider")

    if isinstance(provider, dict):
        openclaw_cfg = provider.get("openclaw")
        if isinstance(openclaw_cfg, dict) and isinstance(openclaw_cfg.get("skill"), str):
            return openclaw_cfg["skill"]
        if isinstance(provider.get("skill"), str):
            return provider["skill"]
        if isinstance(provider.get("ref"), str):
            return provider["ref"]

    provider_ref = tool_spec.get("provider_ref") if isinstance(tool_spec, dict) else None
    return str(provider_ref or tool_name)


def build_scoped_prompt(
    *,
    tool_name: str,
    skill: str,
    description: str,
    original_request: str,
    args: dict[str, Any],
) -> str:
    args_json = json.dumps(args, ensure_ascii=False, sort_keys=True)
    return (
        "You are executing exactly one OpenClaw skill for an Agent-Firewall tool call.\n"
        f"Skill: {skill}\n"
        f"Tool name: {tool_name}\n"
        f"Tool description: {description or tool_name}\n"
        f"Original user request: {original_request or ''}\n"
        f"Tool arguments as JSON: {args_json}\n\n"
        "Use the named skill if it applies. Return only the concise result needed by the caller. "
        "If structured output is useful, return compact JSON-safe text. Do not include hidden reasoning."
    )


def _extract_result(stdout: str) -> str:
    text = stdout.strip()
    if not text:
        return ""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text

    if isinstance(data, dict):
        for key in ("response", "reply", "message", "content", "text", "result", "output"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return json.dumps(data, ensure_ascii=False)
    if isinstance(data, str):
        return data
    return json.dumps(data, ensure_ascii=False)


def _client_from_settings() -> OpenClawClient:
    settings = get_settings()
    return OpenClawClient(
        binary=settings.openclaw_bin,
        timeout_seconds=settings.openclaw_timeout_seconds,
        default_agent_id=settings.openclaw_agent_id,
        local=settings.openclaw_agent_local,
        plugin_stage_dir=settings.openclaw_plugin_stage_dir,
    )


async def execute(
    tool_name: str,
    args: dict[str, Any],
    *,
    tool_spec: dict[str, Any] | None = None,
    session_id: str = "default_user",
    original_request: str = "",
) -> str:
    settings = get_settings()
    client = _client_from_settings()
    skill = _get_openclaw_skill(tool_name, tool_spec)
    description = str(tool_spec.get("description", "")) if isinstance(tool_spec, dict) else ""
    prompt = build_scoped_prompt(
        tool_name=tool_name,
        skill=skill,
        description=description,
        original_request=original_request,
        args=args,
    )

    try:
        payload = await client.agent_message(
            agent_id=settings.openclaw_agent_id,
            session_id=derive_session_id(session_id, tool_name),
            message=prompt,
        )
    except OpenClawError as exc:
        return f"Error executing OpenClaw tool {tool_name}: {exc}"

    result = _extract_result(json.dumps(payload, ensure_ascii=False) if not isinstance(payload, str) else payload)
    if result:
        return result
    return f"OpenClaw tool {tool_name} completed with no output."
