"""Tests for _resolve_direct_llm — provider detection and model formatting.

The agent mirrors proxy-service/src/llm/providers.py detection rules.
These tests ensure the agent's copy stays in sync: wrong prefixes or
missing providers would silently send requests to the wrong provider,
resulting in 401/404 errors from the LLM API.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.agent.nodes.llm_call import _PROVIDER_RULES, _resolve_api_key, _resolve_direct_llm

# ── Helpers ──────────────────────────────────────────────────


def _settings() -> MagicMock:
    s = MagicMock()
    return s


# ── Provider detection rules ────────────────────────────────


class TestProviderRules:
    """Verify _PROVIDER_RULES matches proxy-service/src/llm/providers.py."""

    # The authoritative list from proxy-service
    PROXY_RULES = [
        ("openrouter/", "openrouter"),
        ("deepseek/", "deepseek"),
        ("deepseek-", "deepseek"),
    ]

    def test_rules_match_proxy_service(self):
        """Agent rules must be identical to proxy-service rules.

        If you update proxy-service/src/llm/providers.py:PROVIDER_RULES,
        you MUST update _PROVIDER_RULES in llm_call.py as well.
        """
        assert _PROVIDER_RULES == self.PROXY_RULES, (
            "Agent _PROVIDER_RULES diverged from proxy-service PROVIDER_RULES! "
            "Update apps/agent/src/agent/nodes/llm_call.py to match."
        )


# ── OpenRouter models ───────────────────────────────────────


class TestOpenRouterModels:
    """OpenRouter models → prefix with 'openrouter/'."""

    @pytest.mark.parametrize(
        "model_name,expected",
        [
            ("openrouter/auto", "openrouter/auto"),
            ("anthropic/claude-3.5-sonnet", "openrouter/anthropic/claude-3.5-sonnet"),
        ],
    )
    def test_openrouter_models(self, model_name, expected):
        model, kwargs = _resolve_direct_llm(model_name, "sk-or-test", _settings())
        assert model == expected
        assert kwargs == {"api_key": "sk-or-test"}


# ── DeepSeek models ─────────────────────────────────────────


class TestDeepSeekModels:
    """DeepSeek models → prefix with 'deepseek/'."""

    @pytest.mark.parametrize(
        "model_name,expected",
        [
            ("deepseek-chat", "deepseek/deepseek-chat"),
            ("deepseek-reasoner", "deepseek/deepseek-reasoner"),
            ("deepseek/deepseek-chat", "deepseek/deepseek-chat"),
        ],
    )
    def test_deepseek_models(self, model_name, expected):
        model, kwargs = _resolve_direct_llm(model_name, "sk-ds-test", _settings())
        assert model == expected
        assert kwargs == {"api_key": "sk-ds-test"}


# ── API key forwarding ──────────────────────────────────────


class TestAPIKeyForwarding:
    """Verify api_key is correctly forwarded for external providers."""

    def test_api_key_forwarded_to_openrouter(self):
        _, kwargs = _resolve_direct_llm("openrouter/auto", "sk-or-key-123", _settings())
        assert kwargs["api_key"] == "sk-or-key-123"

    def test_api_key_forwarded_to_deepseek(self):
        _, kwargs = _resolve_direct_llm("deepseek-chat", "sk-ds-key", _settings())
        assert kwargs["api_key"] == "sk-ds-key"

    def test_none_api_key_for_external_provider(self):
        """Even with None api_key, external providers get api_key in kwargs."""
        _, kwargs = _resolve_direct_llm("openrouter/auto", None, _settings())
        assert kwargs == {"api_key": None}


class TestDeepSeekFallback:
    def test_deepseek_env_key_used_when_header_absent(self):
        settings = _settings()
        settings.deepseek_api_key = "sk-env"
        assert _resolve_api_key("deepseek-chat", None, settings) == "sk-env"

    def test_header_key_wins_over_env(self):
        settings = _settings()
        settings.deepseek_api_key = "sk-env"
        assert _resolve_api_key("deepseek-chat", "sk-header", settings) == "sk-header"

    def test_openrouter_does_not_use_deepseek_env(self):
        settings = _settings()
        settings.deepseek_api_key = "sk-env"
        assert _resolve_api_key("openrouter/auto", None, settings) is None
