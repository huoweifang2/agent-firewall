"""Agent graph — LangGraph wiring for the Customer Support Copilot."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

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


def _after_input(state: AgentState) -> str:
    """Route after input: if limit exceeded, short-circuit to memory."""
    if state.get("limit_exceeded"):
        return "memory"
    return "intent"


def _after_llm_call(state: AgentState) -> str:
    """Decide whether LLM returned tool calls or a final response."""
    # Check limit again
    if state.get("limit_exceeded"):
        return "memory"
    fw = state.get("firewall_decision", {})
    if fw.get("decision") == "BLOCK":
        return "memory"

    plan = state.get("tool_plan", [])
    if plan:
        return "pre_tool_gate"

    return "response"


def _after_tool_router(state: AgentState) -> str:
    """Route after deterministic tool planning."""
    if state.get("tool_plan", []):
        return "pre_tool_gate"
    return "llm_call"


def _after_gate(state: AgentState) -> str:
    """Route after pre-tool gate based on decisions.

    - If any tool needs confirmation → pause and ask user.
    - If filtered plan still has tools → execute them.
    - If all tools were blocked → skip to LLM (model answers without tools).
    """
    if state.get("pending_confirmation"):
        return "confirmation_response"
    plan = state.get("tool_plan", [])
    if plan:
        return "tool_executor"
    return "llm_call"


def _confirmation_response_node(state: AgentState) -> AgentState:
    """Build a response asking the user to confirm a sensitive tool call."""
    pending = state.get("pending_confirmation", {})
    tool_name = pending.get("tool", "unknown")
    reason = pending.get("reason", "This tool requires confirmation.")
    args = pending.get("args", {})

    msg = (
        f"⚠️ The action **{tool_name}** requires your confirmation before execution.\n"
        f"Reason: {reason}\n"
        f"Arguments: {args}\n\n"
        f"Please confirm to proceed or cancel the action."
    )
    return {
        **state,
        "final_response": msg,
    }


def build_agent_graph() -> StateGraph:
    """Build and compile the agent LangGraph."""
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("input", input_node)
    graph.add_node("intent", intent_node)
    graph.add_node("policy_check", policy_check_node)
    graph.add_node("tool_router", tool_router_node)
    graph.add_node("pre_tool_gate", pre_tool_gate_node)
    graph.add_node("tool_executor", tool_executor_node)
    graph.add_node("post_tool_gate", post_tool_gate_node)
    graph.add_node("confirmation_response", _confirmation_response_node)
    graph.add_node("llm_call", llm_call_node)
    graph.add_node("memory", memory_node)
    graph.add_node("response", response_node)

    # Wire edges
    graph.set_entry_point("input")

    # After input: check limits
    graph.add_conditional_edges(
        "input",
        _after_input,
        {
            "memory": "memory",
            "intent": "intent",
        },
    )
    graph.add_edge("intent", "policy_check")
    graph.add_edge("policy_check", "tool_router")
    graph.add_conditional_edges(
        "tool_router",
        _after_tool_router,
        {
            "pre_tool_gate": "pre_tool_gate",
            "llm_call": "llm_call",
        },
    )

    # After LLM → check if tools called
    graph.add_conditional_edges(
        "llm_call",
        _after_llm_call,
        {
            "pre_tool_gate": "pre_tool_gate",
            "response": "response",
            "memory": "memory",
        },
    )

    # After gate → execute, skip back to LLM (if all blocked), or ask confirmation
    graph.add_conditional_edges(
        "pre_tool_gate",
        _after_gate,
        {
            "tool_executor": "tool_executor",
            "llm_call": "llm_call",
            "confirmation_response": "confirmation_response",
        },
    )

    # After tool execution → post-tool gate → LLM
    graph.add_edge("tool_executor", "post_tool_gate")
    graph.add_edge("post_tool_gate", "llm_call")

    # Confirmation response → memory → END (returns to user)
    graph.add_edge("confirmation_response", "memory")
    graph.add_edge("response", "memory")
    graph.add_edge("memory", END)

    return graph


# Compiled graph singleton
_compiled_graph = None


def get_agent_graph():
    """Get or build the compiled agent graph (singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        graph = build_agent_graph()
        _compiled_graph = graph.compile()
    return _compiled_graph
