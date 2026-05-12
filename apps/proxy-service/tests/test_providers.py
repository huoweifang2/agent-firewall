"""Tests for provider detection and LiteLLM routing."""

import pytest

from proxy_service.infrastructure.llm.providers import detect_provider, format_litellm_model

# ── detect_provider ──────────────────────────────────────────────


class TestDetectProvider:
    """Test provider detection from model names."""

    @pytest.mark.parametrize(
        "model, expected",
        [
            ("deepseek-chat", "deepseek"),
            ("deepseek-reasoner", "deepseek"),
            ("deepseek/deepseek-chat", "deepseek"),
            ("DEEPSEEK-CHAT", "deepseek"),
        ],
    )
    @pytest.mark.asyncio
    async def test_deepseek(self, model: str, expected: str) -> None:
        assert detect_provider(model) == expected

    @pytest.mark.parametrize(
        "model",
        [
            "gpt-4o",
            "claude-sonnet-4-6",
            "gemini-2.5-flash",
            "mistral-large",
            "openrouter/auto",
        ],
    )
    @pytest.mark.asyncio
    async def test_unsupported(self, model: str) -> None:
        assert detect_provider(model) == "unsupported"

    @pytest.mark.asyncio
    async def test_deepseek_adds_prefix(self) -> None:
        assert format_litellm_model("deepseek-chat", "deepseek") == "deepseek/deepseek-chat"

    @pytest.mark.asyncio
    async def test_deepseek_already_prefixed(self) -> None:
        assert format_litellm_model("deepseek/deepseek-chat", "deepseek") == "deepseek/deepseek-chat"

    @pytest.mark.asyncio
    async def test_unsupported_provider_is_passthrough(self) -> None:
        assert format_litellm_model("gpt-4o", "unsupported") == "gpt-4o"
