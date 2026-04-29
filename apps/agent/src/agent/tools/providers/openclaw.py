"""OpenClaw-backed tool provider."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
from typing import Any

from src.config import get_settings


def derive_session_id(base_session_id: str, tool_name: str) -> str:
    """Derive a stable OpenClaw session id for one Agent-Firewall tool stream."""
    raw = f"{base_session_id}:{tool_name}".encode()
    digest = hashlib.sha256(raw).hexdigest()[:16]
    safe_base = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in base_session_id)[:48]
    return f"agent-firewall-{safe_base}-{digest}"


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


async def execute(
    tool_name: str,
    args: dict[str, Any],
    *,
    tool_spec: dict[str, Any] | None = None,
    session_id: str = "default_user",
    original_request: str = "",
) -> str:
    settings = get_settings()
    skill = _get_openclaw_skill(tool_name, tool_spec)
    description = str(tool_spec.get("description", "")) if isinstance(tool_spec, dict) else ""
    prompt = build_scoped_prompt(
        tool_name=tool_name,
        skill=skill,
        description=description,
        original_request=original_request,
        args=args,
    )

    timeout = max(1, int(settings.openclaw_timeout_seconds))
    command = [
        settings.openclaw_bin,
        "agent",
        "--agent",
        settings.openclaw_agent_id,
        "--session-id",
        derive_session_id(session_id, tool_name),
        "--message",
        prompt,
        "--json",
        "--timeout",
        str(timeout),
    ]
    if settings.openclaw_agent_local:
        command.append("--local")

    try:
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout + 5)
    except TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        return f"Error executing OpenClaw tool {tool_name}: timed out after {timeout} seconds."
    except FileNotFoundError:
        return f"Error executing OpenClaw tool {tool_name}: OpenClaw binary '{settings.openclaw_bin}' was not found."
    except Exception as exc:
        return f"Error executing OpenClaw tool {tool_name}: {exc}"

    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
    if proc.returncode != 0:
        detail = stderr or stdout.strip() or f"exit code {proc.returncode}"
        return f"Error executing OpenClaw tool {tool_name}: {detail}"

    result = _extract_result(stdout)
    if result:
        return result
    return stderr or f"OpenClaw tool {tool_name} completed with no output."
