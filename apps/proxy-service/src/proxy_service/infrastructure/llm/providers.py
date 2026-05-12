"""DeepSeek-only provider detection and routing for LiteLLM."""

from __future__ import annotations

SUPPORTED_PROVIDER = "deepseek"
SUPPORTED_MODELS = {"deepseek-chat", "deepseek-reasoner"}

# Static catalog of supported DeepSeek official API models.
EXTERNAL_MODELS: list[dict[str, str]] = [
    {"id": "deepseek-chat", "provider": "deepseek", "name": "DeepSeek Chat"},
    {"id": "deepseek-reasoner", "provider": "deepseek", "name": "DeepSeek Reasoner"},
]


def detect_provider(model: str) -> str:
    """Detect the provider from a model name.

    Agent-Firewall is intentionally DeepSeek-only for the OpenClaw-first
    runtime. Unsupported providers are rejected by ``llm_completion``.
    """
    model_lower = model.lower()
    if model_lower.startswith(("deepseek", "deepseek/")):
        return SUPPORTED_PROVIDER
    return "unsupported"


def format_litellm_model(model: str, provider: str) -> str:
    """Format a supported DeepSeek model name for LiteLLM."""
    if provider != SUPPORTED_PROVIDER:
        return model

    if model.startswith("deepseek/"):
        return model

    model_id = model
    if model_id not in SUPPORTED_MODELS:
        return model
    return f"deepseek/{model_id}"
