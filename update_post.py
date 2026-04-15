import re

with open("apps/agent-demo/src/agent/nodes/post_tool_gate.py", "r") as f:
    content = f.read()

func_old = """def evaluate_tool_output(
    tool_name: str,
    raw_result: str,
) -> tuple[str, PostGateResult]:"""

func_new = """def is_tool_protected(tool_name: str, x_middlewares: str) -> bool:
    import json
    try:
        mws = json.loads(x_middlewares or "[]")
        for mw in mws:
            app_prefix = mw.get("name", "").upper() + "_"
            if tool_name.upper().startswith(app_prefix):
                return mw.get("protected", False)
    except Exception:
        pass
    return True

def evaluate_tool_output(
    tool_name: str,
    raw_result: str,
    x_middlewares: str = "[]"
) -> tuple[str, PostGateResult]:
    if not is_tool_protected(tool_name, x_middlewares):
        return raw_result, {
            "decision": "PASS",
            "reason": "Unprotected tool bypassed.",
            "secrets_count": 0,
            "pii_count": 0,
            "injection_score": 0.0,
            "tokens_truncated": 0,
            "blocked": False,
        }"""

content = content.replace(func_old, func_new)

with open("apps/agent-demo/src/agent/nodes/post_tool_gate.py", "w") as f:
    f.write(content)
