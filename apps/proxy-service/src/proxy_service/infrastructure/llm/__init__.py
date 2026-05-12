"""LLM client package."""

from proxy_service.infrastructure.llm.client import llm_completion
from proxy_service.infrastructure.llm.exceptions import (
    LLMError,
    LLMModelNotFoundError,
    LLMTimeoutError,
    LLMUpstreamError,
)
from proxy_service.infrastructure.llm.providers import EXTERNAL_MODELS, detect_provider, format_litellm_model

__all__ = [
    "EXTERNAL_MODELS",
    "LLMError",
    "LLMModelNotFoundError",
    "LLMTimeoutError",
    "LLMUpstreamError",
    "detect_provider",
    "format_litellm_model",
    "llm_completion",
]
