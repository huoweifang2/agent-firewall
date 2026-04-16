"""Provider detection and routing for LiteLLM."""

from __future__ import annotations

# Pattern → Provider mapping (order matters: first match wins)
PROVIDER_RULES: list[tuple[str, str]] = [
    # Explicit prefixes (user-provided)
    ("anthropic/", "anthropic"),
    ("gemini/", "google"),
    ("mistral/", "mistral"),
    ("azure/", "azure"),
    # Model name patterns (no prefix needed)
    ("gpt-", "openai"),
    ("o1", "openai"),
    ("o3", "openai"),
    ("claude-", "anthropic"),
    ("gemini-", "google"),
    ("mistral-", "mistral"),
    ("codestral", "mistral"),
]

# Static catalog of well-known external models
EXTERNAL_MODELS: list[dict[str, str]] = [
    # ── DeepSeek (Official API) ──
    {"id": "deepseek-chat", "provider": "deepseek", "name": "DeepSeek Chat"},
    {"id": "deepseek-reasoner", "provider": "deepseek", "name": "DeepSeek Reasoner"},
    # ── Models via OpenRouter ──
    {"id": "openai/gpt-4o", "provider": "openrouter", "name": "GPT-4o"},
    {"id": "openai/gpt-4o-mini", "provider": "openrouter", "name": "GPT-4o"},
    {"id": "openai/gpt-3.5-turbo", "provider": "openrouter", "name": "GPT-3.5 Turbo"},
    {"id": "openai/o1-mini", "provider": "openrouter", "name": "o1 Mini"},
    {"id": "openai/o3-mini", "provider": "openrouter", "name": "o3 Mini"},
    {"id": "anthropic/claude-3.5-sonnet", "provider": "openrouter", "name": "Claude Sonnet 3.5"},
    {"id": "anthropic/claude-3-haiku", "provider": "openrouter", "name": "Claude Haiku 3"},
    {"id": "google/gemini-2.5-pro", "provider": "openrouter", "name": "Gemini 2.5 Pro"},
    {"id": "google/gemini-2.5-flash", "provider": "openrouter", "name": "Gemini 2.5 Flash"},
    {"id": "mistralai/mistral-large", "provider": "openrouter", "name": "Mistral Large"},
]


def detect_provider(model: str) -> str:
    """Detect LLM provider from model name.

    Returns `"openrouter"` as default for unrecognized models.
    """
    model_lower = model.lower()
    if model_lower.startswith("deepseek"):
        return "deepseek"
    return "openrouter"


def format_litellm_model(model: str, provider: str) -> str:
    """Format model name for LiteLLM.

    LiteLLM expects certain prefixes:
    - OpenAI: ``"gpt-4o"`` (as-is, no prefix)
    - Anthropic: ``"anthropic/claude-sonnet-4-6"`` (needs prefix if not present)
    - Google: ``"gemini/gemini-2.5-flash"`` (as-is if prefixed)
    """
    if provider == "deepseek" and not model.startswith("deepseek/"):
        return f"deepseek/{model}"
    if provider != "deepseek" and not model.startswith("openrouter/"):
        return f"openrouter/{model}"
    return model
