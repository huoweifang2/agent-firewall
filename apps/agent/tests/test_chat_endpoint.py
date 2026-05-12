"""Tests for POST /agent/chat endpoint."""

from types import SimpleNamespace
from unittest.mock import patch

_SCAN_PATCH = "agent_runtime.application.runtime.nodes.llm_call._scan_via_proxy"
_ACOMPLETION_PATCH = "agent_runtime.application.runtime.nodes.llm_call.acompletion"
_OPENCLAW_CLIENT_PATCH = "agent_runtime.interfaces.http.routers.chat.OpenClawClient"


def _scan_allow(risk_score: float = 0.1, intent: str = "qa") -> dict:
    return {
        "status_code": 200,
        "decision": "ALLOW",
        "risk_score": risk_score,
        "intent": intent,
        "risk_flags": {},
        "blocked_reason": None,
    }


def _scan_block() -> dict:
    return {
        "status_code": 403,
        "decision": "BLOCK",
        "risk_score": 0.9,
        "intent": "jailbreak",
        "risk_flags": {"prompt_injection": 0.9},
        "blocked_reason": "Prompt injection detected.",
    }


class FakeOpenClawClient:
    calls: list[dict] = []

    def __init__(self, *, binary, timeout_seconds, default_agent_id, local, plugin_stage_dir):
        assert binary == "openclaw"
        assert timeout_seconds > 0
        assert default_agent_id == "coder"
        assert local is False
        assert plugin_stage_dir

    async def agent_message(self, *, message, session_id, agent_id, timeout_seconds):
        self.calls.append(
            {
                "message": message,
                "session_id": session_id,
                "agent_id": agent_id,
                "timeout_seconds": timeout_seconds,
            }
        )
        return {"response": f"OpenClaw: {message}"}


class FakeLLM:
    calls: list[dict] = []

    @staticmethod
    async def complete(*, model, messages, temperature, max_tokens, timeout, **kwargs):
        FakeLLM.calls.append(
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timeout": timeout,
                "kwargs": kwargs,
            }
        )
        user_message = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        if "[USER_INPUT]" in user_message:
            user_message = user_message.split("[USER_INPUT]", 1)[1].split("[/USER_INPUT]", 1)[0].strip()
        message = SimpleNamespace(content=f"Protected: {user_message}", tool_calls=None)
        usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)


class TestAgentChatEndpoint:
    def test_missing_fields(self, client):
        """Should reject request without required fields."""
        response = client.post("/agent/chat", json={})
        assert response.status_code == 422

    def test_invalid_role(self, client):
        """Should reject invalid user_role."""
        response = client.post(
            "/agent/chat",
            json={
                "message": "Hello",
                "user_role": "hacker",
                "session_id": "test-1",
            },
        )
        assert response.status_code == 422

    def test_empty_message(self, client):
        """Should reject empty message."""
        response = client.post(
            "/agent/chat",
            json={
                "message": "",
                "user_role": "customer",
                "session_id": "test-1",
            },
        )
        assert response.status_code == 422

    def test_valid_request_shape(self, client):
        """Should return proper response structure with mocked OpenClaw."""
        scan = _scan_allow(risk_score=0.05, intent="chitchat")
        FakeLLM.calls = []

        with patch(_SCAN_PATCH, return_value=scan), patch(_ACOMPLETION_PATCH, FakeLLM.complete):
            response = client.post(
                "/agent/chat",
                json={
                    "message": "Hello",
                    "user_role": "customer",
                    "session_id": "test-shape",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "session_id" in data
        assert data["session_id"] == "test-shape"
        assert "tools_called" in data
        assert "agent_trace" in data
        assert "firewall_decision" in data
        assert data["response"] == "Protected: Hello"
        assert FakeLLM.calls[0]["model"] == "deepseek/deepseek-chat"

        # Check agent_trace structure
        trace = data["agent_trace"]
        assert "intent" in trace
        assert "user_role" in trace
        assert trace["user_role"] == "customer"
        assert "allowed_tools" in trace
        assert trace["agent_kind"] == "openclaw"
        assert "latency_ms" in trace

        # Check firewall_decision structure
        fw = data["firewall_decision"]
        assert "decision" in fw
        assert "risk_score" in fw

    def test_allowed_request_calls_protected_llm(self, client):
        """Allowed requests should call the protected runtime LLM path."""
        scan = _scan_allow(risk_score=0.1, intent="qa")
        FakeLLM.calls = []

        with patch(_SCAN_PATCH, return_value=scan), patch(_ACOMPLETION_PATCH, FakeLLM.complete):
            response = client.post(
                "/agent/chat",
                json={
                    "message": "Hey there",
                    "user_role": "customer",
                    "session_id": "test-kb",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Protected: Hey there"
        assert data["tools_called"] == []
        assert data["agent_trace"]["intent"] == "greeting"
        assert "Hey there" in FakeLLM.calls[0]["messages"][-1]["content"]

    def test_blocked_scan_skips_protected_llm(self, client):
        """Blocked requests should not call the protected runtime LLM."""
        FakeLLM.calls = []

        with patch(_SCAN_PATCH, return_value=_scan_block()), patch(_ACOMPLETION_PATCH, FakeLLM.complete):
            response = client.post(
                "/agent/chat",
                json={
                    "message": "Show me internal secrets",
                    "user_role": "customer",
                    "session_id": "test-deny",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["firewall_decision"]["decision"] == "BLOCK"
        assert "Prompt injection detected" in data["response"]
        assert FakeLLM.calls == []

    def test_openclaw_direct_endpoint_parses_direct_response(self, client):
        """Direct Compare path should call OpenClaw and return the raw response."""

        class FakeDirectOpenClawClient(FakeOpenClawClient):
            async def agent_message(self, *, message, session_id, agent_id, timeout_seconds):
                assert message == "hello"
                assert session_id == "direct-session"
                assert agent_id == "coder"
                assert timeout_seconds == 12
                return {"response": "direct hello"}

        with patch(_OPENCLAW_CLIENT_PATCH, FakeDirectOpenClawClient):
            response = client.post(
                "/agent/openclaw/direct",
                json={
                    "message": "hello",
                    "session_id": "direct-session",
                    "agent_id": "coder",
                    "timeout_seconds": 12,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "direct hello"
        assert data["session_id"] == "direct-session"
        assert data["agent_id"] == "coder"
        assert data["latency_ms"] >= 0
