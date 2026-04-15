import re

with open("apps/agent-demo/src/agent/nodes/post_tool_gate.py", "r") as f:
    content = f.read()

node_old = """        raw_result = tc.get("result", "")
        sanitized, post_gate = evaluate_tool_output(tc["tool"], raw_result)"""

node_new = """        raw_result = tc.get("result", "")
        x_middlewares = state.get("x_middlewares", "[]")
        sanitized, post_gate = evaluate_tool_output(tc["tool"], raw_result, x_middlewares)"""

content = content.replace(node_old, node_new)

with open("apps/agent-demo/src/agent/nodes/post_tool_gate.py", "w") as f:
    f.write(content)
