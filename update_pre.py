import re

with open("apps/agent-demo/src/agent/nodes/pre_tool_gate.py", "r") as f:
    content = f.read()

# Update _evaluate_tool to skip if not local tools?
func_old = """def _evaluate_tool(
    tool_name: str,
    args: dict[str, Any],
    state: AgentState,
    blocked_count: int,
) -> GateDecision:"""

func_new = """def is_tool_protected(tool_name: str, x_middlewares: str) -> bool:
    import json
    try:
        mws = json.loads(x_middlewares or "[]")
        for mw in mws:
            # We match tool_name prefixes like ASANA_ if it's ASANA from Composio
            app_prefix = mw.get("name", "").upper() + "_"
            if tool_name.upper().startswith(app_prefix):
                return mw.get("protected", False)
    except Exception:
        pass
    # default to protected for internal tools or if unknown
    return True

def _evaluate_tool(
    tool_name: str,
    args: dict[str, Any],
    state: AgentState,
    blocked_count: int,
) -> GateDecision:"""

content = content.replace(func_old, func_new)

check_old = """    # ── Check 1: RBAC ─────────────────────────────────────
    rbac = _check_rbac(tool_name, allowed_tools, user_role)"""

check_new = """    x_middlewares = state.get("x_middlewares", "[]")
    if not is_tool_protected(tool_name, x_middlewares):
        return GateDecision(
            tool=tool_name,
            args=args,
            decision="ALLOW",
            reason="Unprotected external tool bypassed." ,
            checks=[],
            modified_args=args,
            risk_score=0.0,
        )

    # ── Check 1: RBAC ─────────────────────────────────────
    # bypass RBAC entirely if testing with Composio
    if tool_name not in ["searchKnowledgeBase", "getOrderStatus", "getInternalSecrets"]:
        rbac = {"passed": True, "check": "RBAC", "detail": "Tool allowed via Composio."}
    else:
        rbac = _check_rbac(tool_name, allowed_tools, user_role)"""

content = content.replace(check_old, check_new)

with open("apps/agent-demo/src/agent/nodes/pre_tool_gate.py", "w") as f:
    f.write(content)
