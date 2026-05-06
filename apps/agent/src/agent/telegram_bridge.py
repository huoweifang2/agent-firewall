"""Telegram bridge that routes OpenClaw Telegram traffic through Agent-Firewall."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import structlog

from src.agent.interventions import create_intervention, list_interventions, update_intervention
from src.config import Settings, get_settings

logger = structlog.get_logger()

TELEGRAM_API_BASE = "https://api.telegram.org"


def _offset_path() -> Path:
    return Path.home() / ".openclaw" / "agent-firewall" / "telegram-offsets.json"


def _bridge_config_path() -> Path:
    return Path.home() / ".openclaw" / "agent-firewall.json"


@dataclass(slots=True)
class TelegramAccount:
    name: str
    token: str
    allow_from: set[str]
    policy: str
    model: str
    user_role: str
    agent_id: str | None
    poll_timeout_seconds: int
    poll_interval_seconds: float
    drop_pending_on_start: bool


@dataclass(slots=True)
class TelegramBridgeConfig:
    enabled: bool
    accounts: list[TelegramAccount]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _bridge_config_from_openclaw(openclaw_config: dict[str, Any], settings: Settings) -> dict[str, Any]:
    camel = openclaw_config.get("agentFirewall")
    snake = openclaw_config.get("agent_firewall")
    bridge = {}
    if isinstance(camel, dict) and isinstance(camel.get("telegramBridge"), dict):
        bridge = camel["telegramBridge"]
    elif isinstance(snake, dict) and isinstance(snake.get("telegram_bridge"), dict):
        bridge = snake["telegram_bridge"]
    return bridge if isinstance(bridge, dict) else {}


def _as_str_set(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {str(item) for item in value if str(item).strip()}
    return set()


def _account_items(channel: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    accounts = channel.get("accounts")
    if isinstance(accounts, dict) and accounts:
        return [(str(name), data) for name, data in accounts.items() if isinstance(data, dict)]
    return [("default", channel)]


def load_telegram_bridge_config(settings: Settings | None = None) -> TelegramBridgeConfig:
    """Load bridge config from env plus ``~/.openclaw/openclaw.json``.

    Env controls whether the bridge is allowed to run. The OpenClaw config
    provides bot tokens and the takeover flag, but secrets are never returned
    by diagnostics.
    """
    settings = settings or get_settings()
    openclaw_config = _read_json(Path.home() / ".openclaw" / "openclaw.json")
    bridge = _read_json(_bridge_config_path()).get("telegramBridge", {})
    if not isinstance(bridge, dict):
        bridge = {}
    if not bridge:
        bridge = _bridge_config_from_openclaw(openclaw_config, settings)
    channel = openclaw_config.get("channels", {}).get("telegram", {})
    if not isinstance(channel, dict):
        channel = {}

    enabled = bool(settings.telegram_bridge_enabled) and bool(bridge.get("enabled", True))
    default_policy = str(bridge.get("policy") or settings.default_policy)
    default_model = str(bridge.get("model") or settings.default_model)
    default_role = str(bridge.get("userRole") or bridge.get("user_role") or "customer")
    default_agent_id = bridge.get("agentId") or bridge.get("agent_id") or settings.openclaw_agent_id or None
    if isinstance(default_agent_id, str) and not default_agent_id.strip():
        default_agent_id = None

    selected_accounts = _as_str_set(bridge.get("accounts"))
    channel_allow = _as_str_set(channel.get("allowFrom"))
    top_level_token = channel.get("botToken")

    accounts: list[TelegramAccount] = []
    for name, raw_account in _account_items(channel):
        if selected_accounts and name not in selected_accounts:
            continue

        token = raw_account.get("botToken") or top_level_token
        if not isinstance(token, str) or not token.strip():
            continue

        account_bridge = {}
        bridge_accounts = bridge.get("accountOverrides")
        if isinstance(bridge_accounts, dict) and isinstance(bridge_accounts.get(name), dict):
            account_bridge = bridge_accounts[name]

        accounts.append(
            TelegramAccount(
                name=name,
                token=token.strip(),
                allow_from=_as_str_set(raw_account.get("allowFrom")) or channel_allow,
                policy=str(account_bridge.get("policy") or default_policy),
                model=str(account_bridge.get("model") or default_model),
                user_role=str(account_bridge.get("userRole") or account_bridge.get("user_role") or default_role),
                agent_id=account_bridge.get("agentId") or account_bridge.get("agent_id") or default_agent_id,
                poll_timeout_seconds=int(
                    account_bridge.get("pollTimeoutSeconds")
                    or bridge.get("pollTimeoutSeconds")
                    or settings.telegram_bridge_poll_timeout_seconds
                ),
                poll_interval_seconds=float(
                    account_bridge.get("pollIntervalSeconds")
                    or bridge.get("pollIntervalSeconds")
                    or settings.telegram_bridge_poll_interval_seconds
                ),
                drop_pending_on_start=bool(account_bridge.get("dropPendingOnStart", bridge.get("dropPendingOnStart", True))),
            )
        )

    return TelegramBridgeConfig(enabled=enabled, accounts=accounts)


class TelegramBridge:
    def __init__(self, settings: Settings, config: TelegramBridgeConfig) -> None:
        self.settings = settings
        self.config = config
        self._tasks: list[asyncio.Task[None]] = []
        self._approval_task: asyncio.Task[None] | None = None
        self._offset_lock = asyncio.Lock()
        self._last_error: str | None = None
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    @property
    def last_error(self) -> str | None:
        return self._last_error

    async def start(self) -> None:
        if not self.config.enabled or not self.config.accounts:
            return
        self._running = True
        for account in self.config.accounts:
            self._tasks.append(asyncio.create_task(self._poll_account(account)))
        self._approval_task = asyncio.create_task(self._poll_approved_interventions())
        logger.info("telegram_bridge_started", accounts=len(self.config.accounts))

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self._approval_task is not None:
            self._approval_task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        if self._approval_task is not None:
            await asyncio.gather(self._approval_task, return_exceptions=True)
            self._approval_task = None
        self._tasks = []
        logger.info("telegram_bridge_stopped")

    async def _poll_account(self, account: TelegramAccount) -> None:
        async with httpx.AsyncClient(timeout=account.poll_timeout_seconds + 10) as client:
            if account.drop_pending_on_start and self._read_offset(account.name) is None:
                await self._drop_pending(client, account)

            while self._running:
                try:
                    updates = await self._get_updates(client, account)
                    for update in updates:
                        await self._handle_update(client, account, update)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self._last_error = self._redact_error(account, exc)
                    logger.warning("telegram_bridge_poll_failed", account=account.name, error=self._last_error)
                    await asyncio.sleep(max(3.0, account.poll_interval_seconds))

                await asyncio.sleep(max(0.1, account.poll_interval_seconds))

    async def _drop_pending(self, client: httpx.AsyncClient, account: TelegramAccount) -> None:
        try:
            url = self._telegram_url(account, "getUpdates")
            resp = await client.post(url, json={"offset": -1, "limit": 1, "timeout": 0})
            resp.raise_for_status()
            data = resp.json()
            result = data.get("result") if isinstance(data, dict) else None
            if isinstance(result, list) and result:
                update_id = int(result[-1].get("update_id", 0))
                await self._write_offset(account.name, update_id + 1)
        except Exception as exc:
            self._last_error = self._redact_error(account, exc)

    async def _get_updates(self, client: httpx.AsyncClient, account: TelegramAccount) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "timeout": account.poll_timeout_seconds,
            "allowed_updates": ["message"],
        }
        offset = self._read_offset(account.name)
        if offset is not None:
            params["offset"] = offset

        resp = await client.post(self._telegram_url(account, "getUpdates"), json=params)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict) or not data.get("ok"):
            raise RuntimeError("Telegram getUpdates returned a non-ok response")
        result = data.get("result", [])
        return [item for item in result if isinstance(item, dict)]

    async def _handle_update(
        self,
        client: httpx.AsyncClient,
        account: TelegramAccount,
        update: dict[str, Any],
    ) -> None:
        update_id = int(update.get("update_id", 0))
        try:
            message = update.get("message")
            if not isinstance(message, dict):
                return
            if isinstance(message.get("from"), dict) and message["from"].get("is_bot"):
                return

            text = message.get("text")
            if not isinstance(text, str) or not text.strip():
                return

            chat = message.get("chat")
            if not isinstance(chat, dict) or chat.get("id") is None:
                return
            chat_id = str(chat["id"])
            from_id = str((message.get("from") or {}).get("id", ""))
            if account.allow_from and from_id not in account.allow_from and chat_id not in account.allow_from:
                logger.info("telegram_bridge_unauthorized_sender", account=account.name, from_id=from_id)
                return

            response = await self._run_guarded_agent(account, chat_id, text.strip())
            await self._send_message(client, account, chat_id, response)
        finally:
            if update_id:
                await self._write_offset(account.name, update_id + 1)

    async def _run_guarded_agent(
        self,
        account: TelegramAccount,
        chat_id: str,
        text: str,
        *,
        approved_intervention_id: str | None = None,
        create_pause_intervention: bool = True,
    ) -> str:
        async with httpx.AsyncClient(timeout=self.settings.openclaw_timeout_seconds + 30) as client:
            resp = await client.post(
                f"{self.settings.telegram_bridge_agent_base_url.rstrip('/')}/agent/chat",
                json={
                    "message": text,
                    "user_role": account.user_role,
                    "session_id": f"telegram-{account.name}-{chat_id}",
                    "agent_id": account.agent_id,
                    "policy": account.policy,
                    "model": account.model,
                    "approved_intervention_id": approved_intervention_id,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and create_pause_intervention:
                pause = await self._maybe_create_pause_intervention(account, chat_id, text, data)
                if pause:
                    return pause
            response = data.get("response") if isinstance(data, dict) else None
            if isinstance(response, str) and response.strip():
                return response.strip()
            return "Agent-Firewall completed the request, but no response text was returned."

    async def _maybe_create_pause_intervention(
        self,
        account: TelegramAccount,
        chat_id: str,
        text: str,
        data: dict[str, Any],
    ) -> str | None:
        firewall = data.get("firewall_decision") if isinstance(data.get("firewall_decision"), dict) else {}
        pending_confirmation = data.get("pending_confirmation") if isinstance(data.get("pending_confirmation"), dict) else None
        tools_called = data.get("tools_called") if isinstance(data.get("tools_called"), list) else []

        kind = ""
        reason = ""
        risk_score: float | None = None
        tool_payload: dict[str, Any] | None = None
        if firewall.get("decision") == "BLOCK":
            kind = "input_block"
            reason = str(firewall.get("blocked_reason") or "Request blocked by Agent-Firewall.")
            risk_score = float(firewall.get("risk_score") or 0.0)
        elif pending_confirmation:
            kind = "tool_confirmation"
            reason = str(pending_confirmation.get("reason") or "Tool requires operator approval.")
            tool_payload = pending_confirmation
        else:
            blocked_tools = [item for item in tools_called if isinstance(item, dict) and not item.get("allowed", True)]
            if blocked_tools:
                kind = "tool_block"
                reason = str(blocked_tools[0].get("blocked_reason") or "Tool call blocked by Agent-Firewall.")
                tool_payload = blocked_tools[0]

        if not kind:
            return None

        trace = data.get("trace") if isinstance(data.get("trace"), dict) else {}
        intervention = await create_intervention(
            {
                "source": "telegram",
                "account": account.name,
                "chat_id": chat_id,
                "session_id": f"telegram-{account.name}-{chat_id}",
                "kind": kind,
                "message": text,
                "policy": account.policy,
                "model": account.model,
                "reason": reason,
                "risk_score": risk_score,
                "tool_payload": tool_payload,
                "trace_id": trace.get("trace_id"),
            },
            self.settings,
        )
        intervention_id = intervention.get("id") if isinstance(intervention, dict) else None
        suffix = f"\nIntervention: {intervention_id}" if intervention_id else ""
        return f"Agent-Firewall 已暂停这条请求，等待 localhost:3000 控制台审批。\n原因: {reason}{suffix}"

    async def _poll_approved_interventions(self) -> None:
        while self._running:
            try:
                await self._process_approved_interventions()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._last_error = str(exc)[:500]
                logger.warning("telegram_bridge_approval_poll_failed", error=self._last_error)
            await asyncio.sleep(3.0)

    async def _process_approved_interventions(self) -> None:
        accounts = {account.name: account for account in self.config.accounts}
        approved = await list_interventions(status="approved", source="telegram", settings=self.settings)
        if not approved:
            return

        async with httpx.AsyncClient(timeout=self.settings.openclaw_timeout_seconds + 30) as client:
            for item in approved:
                intervention_id = str(item.get("id") or "")
                account = accounts.get(str(item.get("account") or ""))
                chat_id = str(item.get("chat_id") or "")
                message = str(item.get("message") or "")
                if not intervention_id or account is None or not chat_id or not message:
                    continue
                try:
                    response = await self._run_guarded_agent(
                        account,
                        chat_id,
                        message,
                        approved_intervention_id=intervention_id,
                        create_pause_intervention=False,
                    )
                    await self._send_message(client, account, chat_id, response)
                    await update_intervention(
                        intervention_id,
                        {"status": "completed", "result_payload": {"telegram_reply": response[:1000]}},
                        self.settings,
                    )
                except Exception as exc:
                    error = self._redact_error(account, exc)
                    await update_intervention(
                        intervention_id,
                        {"status": "failed", "result_payload": {"error": error}},
                        self.settings,
                    )

    async def _scan(self, account: TelegramAccount, chat_id: str, text: str) -> dict[str, Any]:
        scan_url = f"{self.settings.proxy_base_url.rstrip('/')}/scan"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                scan_url,
                json={
                    "model": account.model,
                    "messages": [{"role": "user", "content": text}],
                    "temperature": self.settings.default_temperature,
                    "max_tokens": self.settings.default_max_tokens,
                    "stream": False,
                },
                headers={
                    "Content-Type": "application/json",
                    "x-client-id": f"telegram-{account.name}",
                    "x-policy": account.policy,
                    "x-correlation-id": f"telegram-{account.name}-{chat_id}",
                },
            )
        if resp.status_code not in (200, 403):
            resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else {}

    async def _send_message(
        self,
        client: httpx.AsyncClient,
        account: TelegramAccount,
        chat_id: str,
        text: str,
    ) -> None:
        chunks = [text[i : i + 3900] for i in range(0, len(text), 3900)] or [""]
        for chunk in chunks:
            resp = await client.post(
                self._telegram_url(account, "sendMessage"),
                json={"chat_id": chat_id, "text": chunk},
            )
            resp.raise_for_status()

    def _telegram_url(self, account: TelegramAccount, method: str) -> str:
        return f"{TELEGRAM_API_BASE}/bot{account.token}/{method}"

    def _read_offsets(self) -> dict[str, int]:
        data = _read_json(_offset_path())
        return {str(key): int(value) for key, value in data.items() if isinstance(value, int)}

    def _read_offset(self, account_name: str) -> int | None:
        return self._read_offsets().get(account_name)

    async def _write_offset(self, account_name: str, offset: int) -> None:
        async with self._offset_lock:
            offset_path = _offset_path()
            offset_path.parent.mkdir(parents=True, exist_ok=True)
            offsets = self._read_offsets()
            offsets[account_name] = offset
            offset_path.write_text(json.dumps(offsets, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _redact_error(account: TelegramAccount, exc: Exception) -> str:
        return str(exc).replace(account.token, "<redacted>")[:500] or type(exc).__name__


_bridge: TelegramBridge | None = None


async def start_telegram_bridge(settings: Settings | None = None) -> TelegramBridge | None:
    global _bridge
    settings = settings or get_settings()
    config = load_telegram_bridge_config(settings)
    _bridge = TelegramBridge(settings, config)
    await _bridge.start()
    return _bridge


async def stop_telegram_bridge() -> None:
    global _bridge
    if _bridge is None:
        return
    await _bridge.stop()
    _bridge = None


def get_telegram_bridge_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    config = load_telegram_bridge_config(settings)
    return {
        "enabled": config.enabled,
        "running": bool(_bridge and _bridge.running),
        "accounts": len(config.accounts),
        "last_error": _bridge.last_error if _bridge else None,
        "offset_path": str(_offset_path()),
    }
