"""Tests for POST /agent/chat endpoint."""

from unittest.mock import AsyncMock, patch

_SCAN_PATCH = "src.agent.nodes.llm_call._scan_via_proxy"
_LLM_PATCH = "src.agent.nodes.llm_call.acompletion"
_OPENCLAW_CLIENT_PATCH = "src.routers.chat.OpenClawClient"


def _scan_allow(risk_score: float = 0.1, intent: str = "qa") -> dict:
    return {
        "status_code": 200,
        "decision": "ALLOW",
        "risk_score": risk_score,
        "intent": intent,
        "risk_flags": {},
        "blocked_reason": None,
    }


def _llm_resp(content: str = "Test response") -> AsyncMock:
    resp = AsyncMock()
    resp.choices = [AsyncMock()]
    resp.choices[0].message.content = content
    resp.usage = AsyncMock()
    resp.usage.prompt_tokens = 50
    resp.usage.completion_tokens = 20
    resp.usage.total_tokens = 70
    return resp


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
        """Should return proper response structure with mocked LLM."""
        scan = _scan_allow(risk_score=0.05, intent="chitchat")
        llm = _llm_resp("Hello! How can I help?")

        with patch(_SCAN_PATCH, return_value=scan), patch(_LLM_PATCH, return_value=llm):
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

        # Check agent_trace structure
        trace = data["agent_trace"]
        assert "intent" in trace
        assert "user_role" in trace
        assert trace["user_role"] == "customer"
        assert "allowed_tools" in trace
        assert "latency_ms" in trace

        # Check firewall_decision structure
        fw = data["firewall_decision"]
        assert "decision" in fw
        assert "risk_score" in fw

    def test_kb_search_response(self, client):
        """KB search should return tool call info."""
        scan = _scan_allow(risk_score=0.1, intent="qa")
        llm = _llm_resp("Our return policy allows returns within 30 days.")

        with patch(_SCAN_PATCH, return_value=scan), patch(_LLM_PATCH, return_value=llm):
            response = client.post(
                "/agent/chat",
                json={
                    "message": "What is your return policy?",
                    "user_role": "customer",
                    "session_id": "test-kb",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["tools_called"]) >= 1
        assert data["tools_called"][0]["tool"] == "searchKnowledgeBase"
        assert data["tools_called"][0]["allowed"] is True
        assert data["agent_trace"]["intent"] == "knowledge_search"

    def test_customer_secrets_denied(self, client):
        """Customer should not be able to call getInternalSecrets."""
        scan = _scan_allow(risk_score=0.3, intent="qa")
        llm = _llm_resp("I don't have access to that.")

        with patch(_SCAN_PATCH, return_value=scan), patch(_LLM_PATCH, return_value=llm):
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
        # getInternalSecrets should not be in allowed_tools
        assert "getInternalSecrets" not in data["agent_trace"]["allowed_tools"]

    def test_openclaw_direct_endpoint_parses_direct_response(self, client):
        """Direct Compare path should call OpenClaw and return the raw response."""

        class FakeOpenClawClient:
            def __init__(self, *, binary, timeout_seconds, default_agent_id, local):
                assert binary == "openclaw"
                assert timeout_seconds > 0
                assert default_agent_id == "coder"
                assert local is False

            async def agent_message(self, *, message, session_id, agent_id, timeout_seconds):
                assert message == "hello"
                assert session_id == "direct-session"
                assert agent_id == "coder"
                assert timeout_seconds == 12
                return {"response": "direct hello"}

        with patch(_OPENCLAW_CLIENT_PATCH, FakeOpenClawClient):
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
