with open("apps/agent-demo/src/agent/nodes/tools.py", "r") as f:
    content = f.read()

# Update tool failure append
func_old = """            error_msg = f"Tool error: {e}"
            tool_calls.append(
                {
                    "tool": tool_name,
                    "args": args,
                    "result": error_msg,
                    "allowed": True,
                }
            )"""

func_new = """            error_msg = f"Tool error: {e}"
            tool_calls.append(
                {
                    "id": call_id,
                    "tool": tool_name,
                    "args": args,
                    "result": error_msg,
                    "allowed": True,
                }
            )"""

content = content.replace(func_old, func_new)

with open("apps/agent-demo/src/agent/nodes/tools.py", "w") as f:
    f.write(content)
