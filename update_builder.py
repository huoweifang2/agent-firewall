with open("apps/agent-demo/src/agent/security/message_builder.py", "r") as f:
    content = f.read()

import_old = """from typing import Any

from src.agent.security.sanitizer import sanitize_chat_history, sanitize_user_input"""

import_new = """from typing import Any
import json

from src.agent.security.sanitizer import sanitize_chat_history, sanitize_user_input"""

content = content.replace(import_old, import_new)

func_old = """def wrap_tool_results(tool_calls: list[dict[str, Any]]) -> dict[str, str] | None:
    \"\"\"Wrap tool results in [TOOL_OUTPUT] delimiters.

    Returns a system message with all tool results, or None if no calls.
    Each result is individually wrapped with anti-instruction markers.
    Uses sanitized_result when available (from post-tool gate).
    \"\"\"
    if not tool_calls:
        return None

    parts: list[str] = []
    for tc in tool_calls:
        tool_name = tc.get("tool", "unknown")
        allowed = tc.get("allowed", False)

        # Use sanitized_result from post-tool gate (spec 03); fall back to raw
        result_text = tc.get("sanitized_result", tc.get("result", ""))

        post_gate = tc.get("post_gate")
        if post_gate and post_gate.get("decision") == "BLOCK":
            status = "BLOCKED"
        elif not allowed:
            status = "DENIED"
        else:
            status = "OK"

        prefix = TOOL_OUTPUT_PREFIX.format(tool_name=tool_name)
        part = f"{prefix}[Status: {status}]\\n{result_text}{TOOL_OUTPUT_SUFFIX}"
        parts.append(part)

    content = "Tool execution results:\\n\\n" + "\\n\\n".join(parts)
    return {"role": "system", "content": content}"""

func_new = """def wrap_tool_results(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not tool_calls:
        return []

    messages = []
    
    assistant_tool_calls = []
    for tc in tool_calls:
        call_id = tc.get("id") or "call_unknown"
        assistant_tool_calls.append({
            "id": call_id,
            "type": "function",
            "function": {
                "name": tc.get("tool", "unknown"),
                "arguments": json.dumps(tc.get("args", {}))
            }
        })
    
    messages.append({
        "role": "assistant",
        "content": None,
        "tool_calls": assistant_tool_calls
    })

    for tc in tool_calls:
        call_id = tc.get("id") or "call_unknown"
        tool_name = tc.get("tool", "unknown")
        allowed = tc.get("allowed", False)
        result_text = tc.get("sanitized_result", tc.get("result", ""))

        post_gate = tc.get("post_gate")
        if post_gate and post_gate.get("decision") == "BLOCK":
            status = "BLOCKED"
        elif not allowed:
            status = "DENIED"
        else:
            status = "OK"

        prefix = TOOL_OUTPUT_PREFIX.format(tool_name=tool_name)
        content = f"{prefix}[Status: {status}]\\n{result_text}{TOOL_OUTPUT_SUFFIX}"

        messages.append({
            "role": "tool",
            "tool_call_id": call_id,
            "name": tool_name,
            "content": content
        })
    
    return messages"""

content = content.replace(func_old, func_new)

node_old = """    # 4. Tool results — wrapped with anti-instruction markers
    tool_calls = state.get("tool_calls", [])
    tool_msg = wrap_tool_results(tool_calls)
    if tool_msg:
        messages.append(tool_msg)"""

node_new = """    # 4. Tool results — wrapped with anti-instruction markers
    tool_calls = state.get("tool_calls", [])
    tool_msgs = wrap_tool_results(tool_calls)
    if tool_msgs:
        messages.extend(tool_msgs)"""

content = content.replace(node_old, node_new)

with open("apps/agent-demo/src/agent/security/message_builder.py", "w") as f:
    f.write(content)
