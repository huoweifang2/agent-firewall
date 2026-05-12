"""Demo-mode LLM provider used when no DeepSeek key is configured."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncGenerator
from types import SimpleNamespace
from typing import Any

MOCK_MODEL_ID = "mock/deepseek-chat"
FALLBACK_RESPONSE = "Agent-Firewall demo mode is running. Configure a DeepSeek key for live model responses."
MOCK_RESPONSES: dict[str, list[str]] = {
    "qa": [
        "This request passed the demo firewall path. A live DeepSeek key is needed for grounded answers.",
        "The protected runtime is reachable. Configure DeepSeek to replace this demo response.",
    ],
    "code_gen": [
        "Demo mode cannot generate production code, but the proxy and audit path are available.",
        "The firewall accepted the coding request in demo mode. Add a DeepSeek key for real output.",
    ],
    "chitchat": [
        "Hello. Agent-Firewall demo mode is running.",
        "Hi. The local proxy is reachable and ready for protected traffic.",
    ],
    "tool_call": [
        "Demo mode recorded the tool-call intent. Real tool execution belongs in the agent runtime.",
        "Tool-call flow is available through the protected runtime graph.",
    ],
}


def _choose_response(intent: str) -> str:
    responses = MOCK_RESPONSES.get(intent)
    if not responses:
        return FALLBACK_RESPONSE
    return responses[0]


def _estimate_tokens(messages: list[dict[str, Any]], completion: str) -> dict[str, int]:
    prompt_tokens = max(1, sum(len(str(message.get("content", "")).split()) for message in messages))
    completion_tokens = max(1, len(completion.split()))
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


def mock_completion(messages: list[dict[str, Any]], intent: str = "qa") -> dict[str, Any]:
    """Return an OpenAI-compatible non-streaming chat completion."""
    content = _choose_response(intent)
    return {
        "id": f"chatcmpl-mock-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": MOCK_MODEL_ID,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": _estimate_tokens(messages, content),
        "_mock": True,
    }


async def mock_completion_stream(
    messages: list[dict[str, Any]],
    intent: str = "qa",
) -> AsyncGenerator[Any, None]:
    """Yield small LiteLLM-like streaming chunks for demo mode."""
    content = _choose_response(intent)
    chunk_id = f"chatcmpl-mock-{uuid.uuid4()}"
    yield SimpleNamespace(
        id=chunk_id,
        model=MOCK_MODEL_ID,
        choices=[SimpleNamespace(index=0, delta=SimpleNamespace(role="assistant", content=None), finish_reason=None)],
    )
    await asyncio.sleep(0)
    yield SimpleNamespace(
        id=chunk_id,
        model=MOCK_MODEL_ID,
        choices=[SimpleNamespace(index=0, delta=SimpleNamespace(role=None, content=content), finish_reason=None)],
    )
    yield SimpleNamespace(
        id=chunk_id,
        model=MOCK_MODEL_ID,
        choices=[SimpleNamespace(index=0, delta=SimpleNamespace(role=None, content=None), finish_reason="stop")],
    )
