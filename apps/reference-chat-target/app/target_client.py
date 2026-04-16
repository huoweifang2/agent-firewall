"""OpenAI-compatible client wrapper for target backend (OpenRouter / DeepSeek).
Supports dual backend pattern:
- RAW -> directly calls OpenRouter / DeepSeek
- PROTECTED -> calls Agent-Firewall proxy endpoint
"""
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from .config import load_settings
from .models import (
    ChatMessage,
    ModelResponse,
    RagSource,
    StreamChunk,
)

logger = logging.getLogger(__name__)
settings = load_settings()

class ModelClient:
    """Unified async client for OpenAI-compatible APIs (OpenRouter, DeepSeek, Agent-Firewall)."""

    def __init__(self, mode: str | None = None) -> None:
        self.mode = mode or settings.app_mode

        if self.mode == "protected":
            # ── Protected HTTP (OpenAI-compatible via Agent-Firewall) ──
            if not settings.agent_firewall_base_url:
                raise ValueError("AGENT_FIREWALL_BASE_URL required for protected mode")

            self._api_key = settings.agent_firewall_api_key
            self._base_url = f"{settings.agent_firewall_base_url}/v1"
            self._model_name = settings.target_model # Pass through to Firewall
        else:
            # ── Direct OpenRouter/DeepSeek HTTP ──
            if not settings.target_api_key:
                 raise ValueError("TARGET_API_KEY required for raw mode")
            
            self._api_key = settings.target_api_key
            self._base_url = settings.target_base_url
            self._model_name = settings.target_model

        self._client = AsyncOpenAI(
            api_key=self._api_key or "dummy",
            base_url=self._base_url,
        )

    def _convert_messages(self, messages: list[ChatMessage], system_prompt: str | None) -> list[dict[str, str]]:
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
            
        for m in messages:
            msgs.append({"role": m.role, "content": m.content})
        return msgs

    async def generate_response(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
        context_sources: list[RagSource] | None = None,
        structured: bool = False,
    ) -> ModelResponse:
        
        system_prompt_str = system_prompt or ""
        if context_sources:
            context_str = "\n\n".join([f"[{s.title}]: {s.content}" for s in context_sources])
            if system_prompt_str:
                system_prompt_str += f"\n\n### Context\n{context_str}"
            else:
                system_prompt_str = f"### Context\n{context_str}"

        msgs = self._convert_messages(messages, system_prompt_str)

        try:
            resp = await self._client.chat.completions.create(
                model=self._model_name,
                messages=msgs,
            )
            content = resp.choices[0].message.content or ""
            return ModelResponse(content=content)
        except Exception as e:
            logger.error(f"Target API Error: {str(e)}")
            raise RuntimeError(f"Target API Error: {str(e)}") from e

    async def generate_stream(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
        context_sources: list[RagSource] | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        
        system_prompt_str = system_prompt or ""
        if context_sources:
            context_str = "\n\n".join([f"[{s.title}]: {s.content}" for s in context_sources])
            if system_prompt_str:
                system_prompt_str += f"\n\n### Context\n{context_str}"
            else:
                system_prompt_str = f"### Context\n{context_str}"

        msgs = self._convert_messages(messages, system_prompt_str)

        try:
            stream = await self._client.chat.completions.create(
                model=self._model_name,
                messages=msgs,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and hasattr(chunk.choices[0], 'delta'):
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        yield StreamChunk(text=delta)
        except Exception as e:
            logger.error(f"Target Stream API Error: {str(e)}")
            yield StreamChunk(text="", error=f"Target Stream API Error: {str(e)}")
