"""Firewall pipeline built on a local sequential runner.

The project no longer depends on an external graph framework here. This module
keeps the historical ``build_pipeline().ainvoke(...)`` interface used by routers
and tests while executing the same nodes directly.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from proxy_service.domain.firewall.pipeline.nodes.decision import decision_node
from proxy_service.domain.firewall.pipeline.nodes.intent import intent_node
from proxy_service.domain.firewall.pipeline.nodes.llm_call import llm_call_node
from proxy_service.domain.firewall.pipeline.nodes.logging_node import logging_node
from proxy_service.domain.firewall.pipeline.nodes.output_filter import output_filter_node
from proxy_service.domain.firewall.pipeline.nodes.parse import parse_node
from proxy_service.domain.firewall.pipeline.nodes.rules import rules_node
from proxy_service.domain.firewall.pipeline.nodes.scanners import parallel_scanners_node
from proxy_service.domain.firewall.pipeline.nodes.transform import transform_node
from proxy_service.domain.firewall.pipeline.state import PipelineState

PipelineNode = Callable[[PipelineState], Awaitable[PipelineState]]


def route_after_decision(state: PipelineState) -> str:
    """Return the post-decision branch name."""
    decision = state.get("decision")
    if decision == "BLOCK":
        return "block"
    if decision == "MODIFY":
        return "modify"
    return "allow"


@dataclass(slots=True)
class SequentialPipeline:
    """Small async pipeline object compatible with the previous graph API."""

    pre_nodes: tuple[PipelineNode, ...]
    include_llm: bool = True

    async def ainvoke(self, state: PipelineState) -> PipelineState:
        result = state
        for node in self.pre_nodes:
            result = await node(result)

        if not self.include_llm:
            return result

        branch = route_after_decision(result)
        if branch == "block":
            return await logging_node(result)
        if branch == "modify":
            result = await transform_node(result)

        result = await llm_call_node(result)
        result = await output_filter_node(result)
        return await logging_node(result)


def build_pre_llm_pipeline() -> SequentialPipeline:
    """Build parse → intent → rules → scanners → decision."""
    return SequentialPipeline(
        pre_nodes=(parse_node, intent_node, rules_node, parallel_scanners_node, decision_node),
        include_llm=False,
    )


def build_pipeline() -> SequentialPipeline:
    """Build the full firewall pipeline.

    Flow:
    parse → intent → rules → scanners → decision
      BLOCK  → logging
      MODIFY → transform → llm_call → output_filter → logging
      ALLOW  → llm_call → output_filter → logging
    """
    return SequentialPipeline(
        pre_nodes=(parse_node, intent_node, rules_node, parallel_scanners_node, decision_node),
        include_llm=True,
    )


pipeline = build_pipeline()
