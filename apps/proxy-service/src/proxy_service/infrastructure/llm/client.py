"""Async LiteLLM client wrapper with DeepSeek-only routing."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from litellm import acompletion
from litellm.exceptions import (
    AuthenticationError,
    NotFoundError,
    ServiceUnavailableError,
    Timeout,
)

from proxy_service.infrastructure.config import get_settings
from proxy_service.infrastructure.llm.exceptions import (
    LLMError,
    LLMModelNotFoundError,
    LLMTimeoutError,
    LLMUpstreamError,
)
from proxy_service.infrastructure.llm.providers import detect_provider, format_litellm_model

_LLM_MAX_RETRIES = 2
_LLM_RETRY_BACKOFF = 1.5  # seconds; doubles each attempt

logger = structlog.get_logger()

# Silence verbose LiteLLM logs at module load
_settings = get_settings()
os.environ.setdefault("LITELLM_LOG", _settings.litellm_log_level)


async def llm_completion(
    messages: list[dict[str, Any]],
    model: str,
    stream: bool = False,
    temperature: float | None = None,
    max_tokens: int | None = None,
    api_key: str | None = None,
    intent: str = "",
) -> Any | AsyncGenerator[Any, None]:
    """Call DeepSeek via LiteLLM.

    The runtime intentionally rejects non-DeepSeek models. The ``api_key``
    parameter may come from the request header as a legacy/dev override;
    otherwise the local DeepSeek key from settings is used.

    Args:
        messages: OpenAI-format message list.
        model: DeepSeek model name (e.g. ``"deepseek-chat"`` or ``"deepseek-reasoner"``).
        stream: Whether to return an async streaming generator.
        temperature: Sampling temperature (0.0–2.0).
        max_tokens: Maximum tokens to generate.
        api_key: Optional API key from browser (``x-api-key`` header).
        intent: Pipeline intent classification (e.g. ``"qa"``, ``"code_gen"``). Used by MockProvider.

    Returns:
        Full response dict (non-streaming) or async generator (streaming).

    Raises:
        LLMError: Missing API key for external provider (401).
        LLMUpstreamError: Provider is unreachable.
        LLMModelNotFoundError: Model does not exist.
        LLMTimeoutError: Request timed out.
    """
    settings = get_settings()

    if temperature is None:
        temperature = settings.default_temperature

    # ── Real provider routing ─────────────────────────────────────
    provider = detect_provider(model)
    if provider != "deepseek":
        raise LLMError("Only DeepSeek official API models are supported by this Agent-Firewall runtime.")

    litellm_model = format_litellm_model(model, provider)

    effective_api_key = api_key or (settings.deepseek_api_key if provider == "deepseek" else "")
    if settings.mode == "demo" and not api_key:
        from proxy_service.infrastructure.llm.mock_provider import mock_completion, mock_completion_stream

        if stream:
            return mock_completion_stream(messages, intent=intent)
        return mock_completion(messages, intent=intent)

    kwargs: dict[str, Any] = {}
    if not effective_api_key:
        raise LLMError(f"API key required for provider '{provider}'. Add your key in Settings → API Keys.")
    kwargs["api_key"] = effective_api_key

    logger.debug(
        "llm_request",
        model=litellm_model,
        provider=provider,
        stream=stream,
        temperature=temperature,
        max_tokens=max_tokens,
        message_count=len(messages),
    )

    last_exc: Exception | None = None
    for attempt in range(_LLM_MAX_RETRIES + 1):
        try:
            response = await acompletion(
                model=litellm_model,
                messages=messages,
                stream=stream,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=settings.request_timeout,
                **kwargs,
            )
            return response
        except AuthenticationError:
            logger.error("llm_auth_error", provider=provider)
            raise LLMError(f"Invalid API key for {provider}. Check your key in Settings → API Keys.") from None
        except ServiceUnavailableError as exc:
            last_exc = exc
            if attempt < _LLM_MAX_RETRIES:
                delay = _LLM_RETRY_BACKOFF * (2**attempt)
                logger.warning(
                    "llm_upstream_retry",
                    provider=provider,
                    attempt=attempt + 1,
                    delay=delay,
                    error=str(exc)[:120],
                )
                await asyncio.sleep(delay)
                continue
            logger.error("llm_upstream_error", error=str(exc), attempts=attempt + 1)
            raise LLMUpstreamError(f"{provider} unavailable after {attempt + 1} attempts: {exc}") from exc
        except NotFoundError as exc:
            logger.error("llm_model_not_found", model=litellm_model, error=str(exc))
            raise LLMModelNotFoundError(f"Model '{model}' not found on {provider}") from exc
        except Timeout as exc:
            logger.error("llm_timeout", model=litellm_model, error=str(exc))
            raise LLMTimeoutError(f"LLM request timed out after {settings.request_timeout}s") from exc
        except Exception as exc:
            safe_msg = str(exc)[:200] if str(exc) else "unknown"
            logger.error("llm_error", model=litellm_model, error_type=type(exc).__name__)
            raise LLMError(f"LLM error ({type(exc).__name__}): {safe_msg}") from exc

    # Should not reach here, but satisfy type checker
    raise LLMUpstreamError(f"{provider} unavailable after retries") from last_exc
