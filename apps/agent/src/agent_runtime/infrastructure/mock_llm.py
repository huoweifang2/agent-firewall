"""Small deterministic LLM used by legacy agent tests."""

from __future__ import annotations

from typing import Any

GENERAL_RESPONSES = [
    "Agent-Firewall demo mode is running.",
    "The protected agent runtime is reachable.",
]


def _latest_user_text(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content", ""))
    return ""


def _latest_tool_text(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "tool":
            return str(message.get("content", ""))
    return ""


def mock_agent_llm(state: dict[str, Any]) -> dict[str, Any]:
    """Return deterministic state updates for demo-mode tests."""
    messages = list(state.get("messages", []))
    tool_text = _latest_tool_text(messages)
    user_text = _latest_user_text(messages).lower()

    if tool_text:
        response = f"I found this result: {tool_text}"
    elif any(keyword in user_text for keyword in ("order", "ticket", "return", "refund", "policy")):
        response = ""
    else:
        response = GENERAL_RESPONSES[0]

    return {
        **state,
        "llm_messages": messages,
        "llm_response": response,
        "firewall_decision": {
            "decision": "ALLOW",
            "risk_score": 0.0,
            "intent": "demo",
            "risk_flags": {},
            "blocked_reason": None,
        },
    }
