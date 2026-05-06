"""ResponseNode — build the final structured response."""

from __future__ import annotations

import structlog

from src.agent.state import AgentState

logger = structlog.get_logger()


def response_node(state: AgentState) -> AgentState:
    """Build the final response text from LLM output or error fallback."""
    # If final_response was already set (e.g. by BLOCK handler), keep it
    if state.get("final_response"):
        logger.info("response_node", source="pre-set", length=len(state["final_response"]))
        return state

    pending = state.get("pending_confirmation")
    if pending:
        tool = pending.get("tool", "tool")
        reason = pending.get("reason") or "This tool requires approval before execution."
        final = f"Agent-Firewall needs approval before running `{tool}`. {reason}"
        logger.info("response_node", source="pending_confirmation", tool=tool, length=len(final))
        return {
            **state,
            "final_response": final,
        }

    blocked = [
        decision
        for decision in state.get("gate_decisions", [])
        if decision.get("decision") == "BLOCK" and decision.get("reason")
    ]
    if blocked and not state.get("tool_plan"):
        reason = blocked[0].get("reason") or "Tool call blocked by Agent-Firewall."
        final = f"Agent-Firewall blocked a tool call: {reason}"
        logger.info("response_node", source="tool_block", length=len(final))
        return {
            **state,
            "final_response": final,
        }

    llm_response = state.get("llm_response", "")

    if llm_response:
        final = llm_response
    elif state.get("intent") == "greeting":
        final = "Hello. I can route tasks through the protected OpenClaw sandbox."
    else:
        final = "I'm sorry, I wasn't able to process your request. Please try again."

    logger.info("response_node", source="llm" if llm_response else "fallback", length=len(final))

    return {
        **state,
        "final_response": final,
    }
