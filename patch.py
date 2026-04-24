import re

with open("apps/agent/src/agent/security/message_builder.py", "r") as f:
    content = f.read()

new_func = '''def wrap_tool_results(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not tool_calls:
        return []

    messages = []
    import uuid

    for tc in tool_calls:
        call_id = tc.get("id")
        if not call_id or call_id == "call_unknown":
            call_id = f"call_{uuid.uuid4().hex[:8]}"
            tc["id"] = call_id

        assistant_tool = {
            "id": call_id,
            "type": "function",
            "function": {
                "name": tc.get("tool", "unknown"),
                "arguments": json.dumps(tc.get("args", {}))
            }
        }
        
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [assistant_tool]
        })
        
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
        content_text = f"{prefix}[Status: {status}]\\n{result_text}{TOOL_OUTPUT_SUFFIX}"

        messages.append({
            "role": "tool",
            "tool_call_id": call_id,
            "name": tool_name,
            "content": content_text
        })

    return messages'''

# Replace the existing function
content = re.sub(
    r"def wrap_tool_results\(tool_calls: list\[dict\[str, Any\]\]\) -> list\[dict\[str, Any\]\]:.*?return messages",
    new_func,
    content,
    flags=re.DOTALL
)

with open("apps/agent/src/agent/security/message_builder.py", "w") as f:
    f.write(content)
