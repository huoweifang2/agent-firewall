"""OpenClaw CLI helpers for wizard tool import and control-plane discovery."""

from __future__ import annotations

import asyncio
import contextlib
import json
import re
from dataclasses import dataclass
from typing import Any

from src.config import get_settings

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s]+"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{16,}"),
)


def redact_openclaw_text(text: str) -> str:
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(
            lambda match: f"{match.group(1)}=<redacted>" if match.lastindex else "<redacted>", redacted
        )
    return redacted


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


@dataclass(slots=True)
class OpenClawClient:
    """Small async wrapper around the local OpenClaw CLI."""

    binary: str
    timeout_seconds: int

    async def run(self, *args: str, timeout_seconds: int | None = None) -> str:
        timeout = max(1, int(timeout_seconds or self.timeout_seconds))
        command = [self.binary, *args]
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout + 5)
        except TimeoutError as exc:
            if proc is not None:
                with contextlib.suppress(ProcessLookupError):
                    proc.kill()
            raise RuntimeError(f"OpenClaw command timed out after {timeout} seconds") from exc
        except FileNotFoundError as exc:
            raise RuntimeError(f"OpenClaw binary '{self.binary}' was not found") from exc

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            detail = stderr or stdout.strip() or f"OpenClaw exited with code {proc.returncode}"
            raise RuntimeError(redact_openclaw_text(detail))
        return stdout

    async def run_json(self, *args: str, timeout_seconds: int | None = None) -> Any:
        return _extract_json_payload(await self.run(*args, timeout_seconds=timeout_seconds))

    async def status(self) -> dict[str, Any]:
        payload = await self.run_json("status", "--json", "--no-usage")
        return payload if isinstance(payload, dict) else {"status": payload}

    async def agents(self) -> list[dict[str, Any]]:
        payload = await self.run_json("agents", "list", "--json")
        return payload if isinstance(payload, list) else list(payload.get("agents", []))

    async def hooks(self) -> list[dict[str, Any]]:
        payload = await self.run_json("hooks", "list", "--json")
        hooks = payload.get("hooks", payload) if isinstance(payload, dict) else payload
        if not isinstance(hooks, list):
            raise RuntimeError("OpenClaw hooks output has an unexpected shape")
        return [hook for hook in hooks if isinstance(hook, dict)]

    async def models_status(self) -> dict[str, Any]:
        payload = await self.run_json("models", "status", "--json")
        return payload if isinstance(payload, dict) else {"models": payload}

    async def skills(self, *, eligible_only: bool = True) -> list[dict[str, Any]]:
        payload = await self.run_json("skills", "list", "--json")
        skills = payload.get("skills", payload) if isinstance(payload, dict) else payload
        if not isinstance(skills, list):
            raise RuntimeError("OpenClaw skills output has an unexpected shape")
        if eligible_only:
            return [skill for skill in skills if isinstance(skill, dict) and bool(skill.get("eligible", False))]
        return [skill for skill in skills if isinstance(skill, dict)]


def get_openclaw_client() -> OpenClawClient:
    settings = get_settings()
    return OpenClawClient(binary=settings.openclaw_bin, timeout_seconds=settings.openclaw_timeout_seconds)


async def get_openclaw_status() -> dict[str, Any]:
    return await get_openclaw_client().status()


async def list_openclaw_agents() -> list[dict[str, Any]]:
    return [_redact_agent(item) for item in await get_openclaw_client().agents()]


async def list_openclaw_hooks() -> list[dict[str, Any]]:
    return [_redact_hook(item) for item in await get_openclaw_client().hooks()]


async def get_openclaw_models_status() -> dict[str, Any]:
    return await get_openclaw_client().models_status()


async def list_openclaw_skills(*, eligible_only: bool = True) -> list[dict[str, Any]]:
    skills = await get_openclaw_client().skills(eligible_only=eligible_only)
    redacted: list[dict[str, Any]] = []
    for item in skills:
        redacted.append(_redact_skill(item))
    return redacted


def _redact_skill(item: dict[str, Any]) -> dict[str, Any]:
    return {
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


def _redact_agent(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id", "")),
        "name": str(item.get("name", "")),
        "workspace": item.get("workspace"),
        "model": item.get("model"),
        "bindings": item.get("bindings", 0),
        "is_default": bool(item.get("isDefault", False)),
    }


def _redact_hook(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": str(item.get("name", "")),
        "description": str(item.get("description", "")),
        "emoji": item.get("emoji"),
        "eligible": bool(item.get("eligible", False)),
        "disabled": bool(item.get("disabled", False)),
        "enabled_by_config": bool(item.get("enabledByConfig", False)),
        "requirements_satisfied": bool(item.get("requirementsSatisfied", False)),
        "loadable": bool(item.get("loadable", False)),
        "source": item.get("source"),
        "events": item.get("events") if isinstance(item.get("events"), list) else [],
        "homepage": item.get("homepage"),
        "missing": item.get("missing") if isinstance(item.get("missing"), dict) else {},
        "managed_by_plugin": bool(item.get("managedByPlugin", False)),
    }


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
