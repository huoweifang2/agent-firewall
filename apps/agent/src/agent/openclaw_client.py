"""OpenClaw CLI client for the agent runtime."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(
        r"(?i)(['\"]?(?:api[_-]?key|access[_-]?token|accesstoken|refresh[_-]?token|refreshtoken|token|secret|password)['\"]?\s*[:=]\s*['\"]?)[^'\"\s,}]+"
    ),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{16,}"),
)


class OpenClawError(RuntimeError):
    """Raised when the OpenClaw CLI cannot complete a command."""


@dataclass(slots=True)
class OpenClawClient:
    """Small async wrapper around the local OpenClaw CLI."""

    binary: str = "openclaw"
    timeout_seconds: int = 120
    default_agent_id: str = "coder"
    local: bool = False
    plugin_stage_dir: str | None = None

    async def run(self, *args: str, timeout_seconds: int | None = None) -> str:
        """Run an OpenClaw command and return stdout."""
        timeout = max(1, int(timeout_seconds or self.timeout_seconds))
        command = [self.binary, *args]
        env = self._subprocess_env()
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout + 5)
        except TimeoutError as exc:
            if proc is not None:
                with contextlib.suppress(ProcessLookupError):
                    proc.kill()
            raise OpenClawError(f"OpenClaw command timed out after {timeout} seconds.") from exc
        except FileNotFoundError as exc:
            raise OpenClawError(f"OpenClaw binary '{self.binary}' was not found.") from exc
        except Exception as exc:
            raise OpenClawError(f"OpenClaw command failed: {self.redact(str(exc))}") from exc

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            detail = stderr or stdout.strip() or f"exit code {proc.returncode}"
            raise OpenClawError(self.redact(detail))
        return stdout

    def _subprocess_env(self) -> dict[str, str]:
        env = os.environ.copy()
        stage_dir = (self.plugin_stage_dir or "").strip()
        if stage_dir:
            resolved = Path(stage_dir).expanduser()
            resolved.mkdir(parents=True, exist_ok=True)
            env.setdefault("OPENCLAW_PLUGIN_STAGE_DIR", str(resolved))
        return env

    async def run_json(self, *args: str, timeout_seconds: int | None = None) -> Any:
        """Run an OpenClaw command and parse the JSON payload from stdout."""
        stdout = await self.run(*args, timeout_seconds=timeout_seconds)
        return extract_json_payload(stdout)

    async def agent_message(
        self,
        *,
        message: str,
        session_id: str,
        agent_id: str | None = None,
        timeout_seconds: int | None = None,
    ) -> Any:
        """Send one message to an OpenClaw agent and return its parsed JSON or text result."""
        timeout = max(1, int(timeout_seconds or self.timeout_seconds))
        command = [
            "agent",
            "--agent",
            agent_id or self.default_agent_id,
            "--session-id",
            session_id,
            "--message",
            message,
            "--json",
            "--timeout",
            str(timeout),
        ]
        if self.local:
            command.append("--local")

        stdout = await self.run(*command, timeout_seconds=timeout)
        text = stdout.strip()
        if not text:
            return ""
        try:
            return extract_json_payload(text)
        except OpenClawError:
            return text

    async def status(self) -> dict[str, Any]:
        payload = await self.run_json("status", "--json", "--no-usage")
        return payload if isinstance(payload, dict) else {"status": payload}

    async def list_agents(self) -> list[dict[str, Any]]:
        payload = await self.run_json("agents", "list", "--json")
        return payload if isinstance(payload, list) else list(payload.get("agents", []))

    async def list_skills(self, *, eligible_only: bool = True) -> list[dict[str, Any]]:
        payload = await self.run_json("skills", "list", "--json")
        skills = payload.get("skills", payload) if isinstance(payload, dict) else payload
        if not isinstance(skills, list):
            raise OpenClawError("OpenClaw skills output has an unexpected shape.")
        if eligible_only:
            return [item for item in skills if isinstance(item, dict) and bool(item.get("eligible", False))]
        return [item for item in skills if isinstance(item, dict)]

    async def list_hooks(self) -> list[dict[str, Any]]:
        payload = await self.run_json("hooks", "list", "--json")
        hooks = payload.get("hooks", payload) if isinstance(payload, dict) else payload
        if not isinstance(hooks, list):
            raise OpenClawError("OpenClaw hooks output has an unexpected shape.")
        return [item for item in hooks if isinstance(item, dict)]

    async def models_status(self) -> dict[str, Any]:
        payload = await self.run_json("models", "status", "--json")
        return payload if isinstance(payload, dict) else {"models": payload}

    async def list_models(self, *, provider: str = "deepseek") -> list[dict[str, Any]]:
        payload = await self.run_json("models", "list", "--provider", provider, "--json")
        models = payload.get("models", payload) if isinstance(payload, dict) else payload
        if not isinstance(models, list):
            raise OpenClawError("OpenClaw models output has an unexpected shape.")
        return [item for item in models if isinstance(item, dict)]

    @staticmethod
    def redact(text: str) -> str:
        redacted = text
        for pattern in _SECRET_PATTERNS:
            redacted = pattern.sub(
                lambda match: f"{match.group(1)}<redacted>" if match.lastindex else "<redacted>", redacted
            )
        return redacted


def derive_session_id(base_session_id: str, tool_name: str) -> str:
    """Derive a stable OpenClaw session id for one Agent-Firewall tool stream."""
    raw = f"{base_session_id}:{tool_name}".encode()
    digest = hashlib.sha256(raw).hexdigest()[:16]
    safe_base = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in base_session_id)[:48]
    return f"agent-firewall-{safe_base}-{digest}"


def extract_json_payload(stdout: str) -> Any:
    """Parse JSON from stdout, tolerating banner text before the payload."""
    text = stdout.strip()
    if not text:
        raise OpenClawError("OpenClaw returned no output.")

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
    raise OpenClawError("OpenClaw output did not contain JSON.")
