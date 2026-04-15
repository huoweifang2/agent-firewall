import re

with open("apps/agent-demo/src/agent/nodes/tools.py", "r") as f:
    content = f.read()

# Update tool_executor_node to store tool call ID
func_old = """    for plan in plans:
        tool_name = plan["tool"]
        args = plan.get("args", {})

        # Rely on pre-tool gate for safety now instead of strict local list.
        try:
            t0 = time.perf_counter()
            result = execute_tool(tool_name, args)
            dur_ms = int((time.perf_counter() - t0) * 1000)
            tool_calls.append(
                {
                    "tool": tool_name,
                    "args": args,
                    "result": result,
                    "allowed": True,
                }
            )"""

func_new = """    for plan in plans:
        tool_name = plan["tool"]
        args = plan.get("args", {})
        call_id = plan.get("id", "call_unknown")

        # Rely on pre-tool gate for safety now instead of strict local list.
        try:
            t0 = time.perf_counter()
            result = execute_tool(tool_name, args)
            dur_ms = int((time.perf_counter() - t0) * 1000)
            tool_calls.append(
                {
                    "id": call_id,
                    "tool": tool_name,
                    "args": args,
                    "result": result,
                    "allowed": True,
                }
            )"""

content = content.replace(func_old, func_new)

with open("apps/agent-demo/src/agent/nodes/tools.py", "w") as f:
    f.write(content)
print("done")
