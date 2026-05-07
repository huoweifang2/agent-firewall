"""Agent runtime graph for Telegram-first Agent-Firewall execution.

The runtime uses a small in-process graph adapter with ``compile`` and
``ainvoke`` methods so the node boundaries stay explicit without an external
graph framework dependency.
"""

from __future__ import annotations

from typing import Any

import structlog

from src.agent.nodes.input import input_node
from src.agent.nodes.intent import intent_node
from src.agent.nodes.llm_call import llm_call_node
from src.agent.nodes.memory import memory_node
from src.agent.nodes.policy import policy_check_node
from src.agent.nodes.post_tool_gate import post_tool_gate_node
from src.agent.nodes.pre_tool_gate import pre_tool_gate_node
from src.agent.nodes.response import response_node
from src.agent.nodes.tools import tool_executor_node, tool_router_node
from src.agent.state import AgentState
from src.config import get_settings

logger = structlog.get_logger()


def _after_input(state: AgentState) -> str:
    """Route after input validation."""
    if state.get("limit_exceeded") and state.get("final_response"):
        return "memory"
    return "intent"


def _check_blocked(state: AgentState) -> str:
    """Route after the LLM/firewall call."""
    if state.get("limit_exceeded"):
        return "memory"
    return "response"


def _has_tool_work(state: AgentState) -> bool:
    return bool(state.get("tool_plan")) and not bool(state.get("pending_confirmation"))


def _should_stop_for_gate(state: AgentState, had_plans: bool) -> bool:
    if state.get("pending_confirmation"):
        return True
    return had_plans and not state.get("tool_plan")


class AgentRuntimeGraph:
    """Small async runner that executes the agent nodes in order."""

    def compile(self) -> AgentRuntimeGraph:
        return self

    async def ainvoke(self, initial_state: dict[str, Any]) -> AgentState:
        settings = get_settings()
        state: AgentState = dict(initial_state)
        state["policy"] = state.get("policy") or settings.default_policy
        state["model"] = state.get("model") or settings.default_model

        state = await input_node(state)
        if _after_input(state) == "memory":
            return memory_node(state)

        state = intent_node(state)
        state = policy_check_node(state)

        # Legacy no-runtime mode still has deterministic tools. Runtime-configured
        # OpenClaw/MCP tools are selected by the model in llm_call_node.
        state = tool_router_node(state)
        if state.get("tool_plan"):
            state = pre_tool_gate_node(state)
            if not _should_stop_for_gate(state, had_plans=True) and _has_tool_work(state):
                state = await tool_executor_node(state)
                state = post_tool_gate_node(state)

        max_iterations = max(1, int(state.get("max_iterations") or settings.max_iterations))
        llm_turns = 0
        while llm_turns < max_iterations:
            llm_turns += 1
            state = await llm_call_node(state)

            if state.get("final_response") or _check_blocked(state) == "memory":
                break

            tool_plan = list(state.get("tool_plan", []))
            if not tool_plan:
                break

            state = pre_tool_gate_node(state)
            if _should_stop_for_gate(state, had_plans=bool(tool_plan)):
                break

            state = await tool_executor_node(state)
            state = post_tool_gate_node(state)

        if llm_turns >= max_iterations and state.get("tool_plan") and not state.get("final_response"):
            state = {
                **state,
                "final_response": "Agent-Firewall stopped the request after reaching the tool iteration limit.",
                "limit_exceeded": state.get("limit_exceeded") or "max_iterations",
            }

        state = response_node(state)
        state = memory_node(state)
        logger.info(
            "agent_runtime_graph_complete",
            session_id=state.get("session_id"),
            tool_calls=len(state.get("tool_calls", [])),
            pending_confirmation=bool(state.get("pending_confirmation")),
        )
        return state


_graph: AgentRuntimeGraph | None = None


def build_agent_graph() -> AgentRuntimeGraph:
    return AgentRuntimeGraph()


def get_agent_graph() -> AgentRuntimeGraph:
    global _graph
    if _graph is None:
        _graph = build_agent_graph().compile()
    return _graph
