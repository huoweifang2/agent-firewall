"""OpenClaw CLI helpers for wizard tool import."""

from __future__ import annotations

import asyncio
import contextlib
import json
import re
from typing import Any

from src.config import get_settings


def _extract_json_payload(stdout: str) -> Any:
    text = stdout.strip()
    if not text:
        raise ValueError("OpenClaw returned no output")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch not in "[{":
            continue
        try:
            payload, _end = decoder.raw_decode(text[idx:])
            return payload
        except json.JSONDecodeError:
            continue
    raise ValueError("OpenClaw output did not contain JSON")


async def list_openclaw_skills(*, eligible_only: bool = True) -> list[dict[str, Any]]:
    settings = get_settings()
    command = [settings.openclaw_bin, "skills", "list", "--json"]
    try:
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(),
            timeout=max(1, settings.openclaw_timeout_seconds),
        )
    except TimeoutError as exc:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        raise RuntimeError("OpenClaw skills listing timed out") from exc
    except FileNotFoundError as exc:
        raise RuntimeError(f"OpenClaw binary '{settings.openclaw_bin}' was not found") from exc

    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
    if proc.returncode != 0:
        raise RuntimeError(stderr or stdout.strip() or f"OpenClaw exited with code {proc.returncode}")

    payload = _extract_json_payload(stdout)
    skills = payload.get("skills", payload) if isinstance(payload, dict) else payload
    if not isinstance(skills, list):
        raise RuntimeError("OpenClaw skills output has an unexpected shape")

    redacted: list[dict[str, Any]] = []
    for item in skills:
        if not isinstance(item, dict):
            continue
        if eligible_only and not bool(item.get("eligible", False)):
            continue
        redacted.append(
            {
                "name": str(item.get("name", "")),
                "description": str(item.get("description", "")),
                "source": item.get("source"),
                "bundled": bool(item.get("bundled", False)),
                "eligible": bool(item.get("eligible", False)),
                "disabled": bool(item.get("disabled", False)),
                "blocked_by_allowlist": bool(item.get("blockedByAllowlist", False)),
                "emoji": item.get("emoji"),
                "homepage": item.get("homepage"),
                "missing": item.get("missing") if isinstance(item.get("missing"), dict) else {},
            }
        )
    return redacted


def openclaw_tool_name(skill_name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", skill_name.strip()).strip("_").lower()
    return f"openclaw_{slug or 'skill'}"[:64]


def openclaw_arg_schema(skill_name: str) -> dict[str, Any]:
    return {
        "provider": {
            "ref": skill_name,
            "openclaw": {"skill": skill_name},
            "protection": {
                "pre_gate_enabled": True,
                "post_gate_enabled": True,
            },
            "properties": {
                "request": {
                    "type": "string",
                    "description": "Concrete request to execute with this OpenClaw skill.",
                }
            },
            "required": ["request"],
        }
    }
