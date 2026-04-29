"""ToolRouterNode + ToolExecutorNode — plan and execute tool calls."""

from __future__ import annotations

import re
import time

import structlog

from src.agent.runtime_access import get_sub_agent_by_delegate_tool, is_delegate_tool_name
from src.agent.state import AgentState, ToolCallRecord
from src.agent.tools.commerce import extract_status_from_message
from src.agent.tools.hub import execute_tool_call
from src.agent.trace.accumulator import TraceAccumulator

logger = structlog.get_logger()


def _select_tools_for_intent(state: AgentState) -> list[dict]:
    """Select which tools to call based on intent and message content.

    Returns a list of tool call plans: [{"tool": name, "args": {...}}].
    This is a deterministic router — no LLM needed.
    """
    intent = state.get("intent", "unknown")
    allowed = state.get("allowed_tools", [])
    message = state.get("message", "").lower()
    plans: list[dict] = []

    if intent == "order_query":
        # Extract order ID from message — supports:
        #   "ORD-12345", "ord-123", "#12345", "order #12345", bare digits
        order_match = re.search(r"ord-(\d{3,6})", message)
        if not order_match:
            # Try "#<digits>" or "order <digits>" or "order#<digits>"
            order_match = re.search(r"(?:order\s*)?#?\s*(\d{3,6})\b", message)
        if order_match:
            digits = order_match.group(1)
            order_id = f"ORD-{digits}"
        else:
            order_id = ""
        if "getOrderStatus" in allowed:
            plans.append({"tool": "getOrderStatus", "args": {"order_id": order_id or "unknown"}})
        elif "getOrders" in allowed:
            plans.append({"tool": "getOrders", "args": {"order_id": order_id}})

    elif intent == "knowledge_search":
        if "searchKnowledgeBase" in allowed:
            plans.append({"tool": "searchKnowledgeBase", "args": {"query": state.get("message", "")}})
        elif "searchProducts" in allowed:
            plans.append({"tool": "searchProducts", "args": {"query": state.get("message", "")}})

    elif intent == "admin_action":
        if "updateOrder" in allowed and "update order" in message:
            status = extract_status_from_message(message) or "processing"
            order_match = re.search(r"ord-(\d{3,6})", message)
            order_id = f"ORD-{order_match.group(1)}" if order_match else "ORD-001"
            plans.append({"tool": "updateOrder", "args": {"order_id": order_id, "status": status}})

        elif "updateUser" in allowed and "update user" in message:
            user_match = re.search(r"usr-(\d{3,6})", message)
            email_match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", message)
            phone_match = re.search(r"\+?\d[\d\- ]{7,}", message)
            user_id = f"USR-{user_match.group(1)}" if user_match else "USR-001"
            plans.append(
                {
                    "tool": "updateUser",
                    "args": {
                        "user_id": user_id,
                        "email": email_match.group(0) if email_match else "",
                        "phone": phone_match.group(0) if phone_match else "",
                    },
                }
            )

        elif "getUsers" in allowed and any(kw in message for kw in ["user", "users", "customer", "customers"]):
            plans.append({"tool": "getUsers", "args": {"query": state.get("message", "")}})

        # Try secrets first if allowed, also search KB for context
        elif "getInternalSecrets" in allowed:
            plans.append({"tool": "getInternalSecrets", "args": {}})
        if "searchKnowledgeBase" in allowed and any(kw in message for kw in ["info", "help", "how"]):
            plans.append({"tool": "searchKnowledgeBase", "args": {"query": state.get("message", "")}})
        elif "searchProducts" in allowed and any(kw in message for kw in ["product", "products", "catalog"]):
            plans.append({"tool": "searchProducts", "args": {"query": state.get("message", "")}})

    elif intent == "greeting":
        # No tools needed for greetings
        pass

    elif intent == "unknown":
        # Default: try KB search
        if "searchKnowledgeBase" in allowed:
            plans.append({"tool": "searchKnowledgeBase", "args": {"query": state.get("message", "")}})
        elif "searchProducts" in allowed:
            plans.append({"tool": "searchProducts", "args": {"query": state.get("message", "")}})

    return plans


def tool_router_node(state: AgentState) -> AgentState:
    """Plan which tools to call based on intent and role."""
    plans = _select_tools_for_intent(state)

    # Trace (spec 07)
    trace = TraceAccumulator(state.get("trace"))
    trace.start_iteration()
    trace.record_tool_plan(plans)

    logger.info("tool_router_node", tool_count=len(plans), tools=[p["tool"] for p in plans])

    return {
        **state,
        "tool_plan": plans,
        "trace": trace.data,
    }


async def tool_executor_node(state: AgentState) -> AgentState:
    """Execute planned tool calls and collect results.

    Only executes tools that passed the pre-tool gate (tool_plan is
    already filtered by pre_tool_gate_node). The RBAC check here is
    kept as a safety net.
    """
    plans = state.get("tool_plan", [])
    tool_calls: list[ToolCallRecord] = list(state.get("tool_calls", []))
    iterations = state.get("iterations", 0)
    trace = TraceAccumulator(state.get("trace"))

    for plan in plans:
        tool_name = plan["tool"]
        args = plan.get("args", {})
        call_id = plan.get("id", "call_unknown")

        try:
            t0 = time.perf_counter()
            result = await execute_tool_call(state, tool_name, args)
            dur_ms = int((time.perf_counter() - t0) * 1000)
            tool_calls.append(
                {
                    "id": call_id,
                    "tool": tool_name,
                    "args": args,
                    "result": result,
                    "allowed": True,
                }
            )
            # Trace (spec 07)
            trace.record_tool_execution(tool_name, args, result, dur_ms)
            if tool_name == "createSubAgent":
                trace.record_tool_flow(
                    event="create_subagent",
                    tool=tool_name,
                    delegated_to=str(args.get("name", "")),
                    task=str(args.get("description", "")),
                    result_preview=result,
                )
            elif is_delegate_tool_name(state.get("runtime_spec"), tool_name):
                sub_agent = get_sub_agent_by_delegate_tool(state.get("runtime_spec"), tool_name) or {}
                trace.record_tool_flow(
                    event="delegate_task",
                    tool=tool_name,
                    delegated_to=str(sub_agent.get("name", tool_name)),
                    task=str(args.get("task", "")),
                    result_preview=result,
                )
            logger.info("tool_executed", tool=tool_name, result_len=len(result))
        except Exception as e:
            error_msg = f"Tool error: {e}"
            tool_calls.append(
                {
                    "id": call_id,
                    "tool": tool_name,
                    "args": args,
                    "result": error_msg,
                    "allowed": True,
                }
            )
            logger.error("tool_error", tool=tool_name, error=str(e))

    return {
        **state,
        "tool_calls": tool_calls,
        "iterations": iterations + 1,
        "trace": trace.data,
    }
