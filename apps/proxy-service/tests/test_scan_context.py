"""Tests for shared scan context across pipeline nodes."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from proxy_service.application.services.denylist import DenylistHit
from proxy_service.domain.firewall.pipeline.graph import build_pre_llm_pipeline
from proxy_service.domain.firewall.pipeline.state import PipelineState


def _state() -> PipelineState:
    return {
        "request_id": "scan-context-test",
        "client_id": "test",
        "policy_name": "balanced",
        "policy_config": {"thresholds": {"max_risk": 0.7}},
        "model": "deepseek/deepseek-chat",
        "messages": [{"role": "user", "content": "please summarize this"}],
        "user_message": "",
        "prompt_hash": "",
        "temperature": 0.7,
        "max_tokens": None,
        "stream": False,
    }


@patch("proxy_service.domain.firewall.pipeline.nodes.rules.check_denylist", new_callable=AsyncMock)
@patch("proxy_service.domain.firewall.pipeline.nodes.intent.check_denylist", new_callable=AsyncMock)
async def test_denylist_hits_are_loaded_once_and_reused(mock_intent_deny: AsyncMock, mock_rules_deny: AsyncMock):
    hit = DenylistHit(
        phrase="summarize",
        category="general",
        action="score_boost",
        severity="low",
        is_regex=False,
        description="soft signal",
    )
    mock_intent_deny.return_value = [hit]
    mock_rules_deny.side_effect = AssertionError("rules_node should reuse cached denylist hits")

    result = await build_pre_llm_pipeline().ainvoke(_state())

    mock_intent_deny.assert_awaited_once()
    mock_rules_deny.assert_not_awaited()
    assert result["denylist_hits"] == [hit]
    assert result["risk_flags"]["score_boost"] == 0.1
