from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_llm_completion_uses_deepseek_env_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-env-fallback")

    from src.config import get_settings

    get_settings.cache_clear()

    import src.llm.client as client_mod

    captured: dict = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(choices=[], usage=None)

    monkeypatch.setattr(client_mod, "acompletion", fake_acompletion)

    await client_mod.llm_completion(
        messages=[{"role": "user", "content": "hello"}],
        model="deepseek/deepseek-chat",
    )

    assert captured["api_key"] == "sk-env-fallback"
    assert captured["model"] == "deepseek/deepseek-chat"
    get_settings.cache_clear()
