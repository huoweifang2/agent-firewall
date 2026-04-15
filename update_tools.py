with open("apps/agent-demo/src/agent/nodes/tools.py", "r") as f:
    content = f.read()

func_old = """    for plan in plans:
        tool_name = plan["tool"]
        args = plan.get("args", {})

        # Safety net — pre_tool_gate should have already filtered,
        # but double-check RBAC as defense in depth.
        if tool_name not in allowed:
            tool_calls.append(
                {
                    "tool": tool_name,
                    "args": args,
                    "result": f"Access denied: {tool_name} is not available for your role.",
                    "allowed": False,
                }
            )
            logger.warning("tool_denied", tool=tool_name, role=state.get("user_role"))
            continue

        try:"""

func_new = """    for plan in plans:
        tool_name = plan["tool"]
        args = plan.get("args", {})

        # Rely on pre-tool gate for safety now instead of strict local list.
        try:"""

if func_old in content:
    content = content.replace(func_old, func_new)
    with open("apps/agent-demo/src/agent/nodes/tools.py", "w") as f:
        f.write(content)
    print("Updated tools.py")
else:
    print("Could not find func_old in tools.py")
