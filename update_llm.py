import re

with open("apps/agent-demo/src/agent/nodes/llm_call.py", "r") as f:
    content = f.read()

# ADD IMPORTS
import_insert = "\nfrom litellm.exceptions import APIError\nfrom src.agent.tools.registry import get_llm_tool_schemas\n"
content = content.replace("\nfrom litellm.exceptions import APIError\n", import_insert)

# UPDATE LITELMM CALL
acompletion_old = """        direct_model, direct_kwargs = _resolve_direct_llm(model_name, api_key, settings)

        full_resp = await acompletion(
            model=direct_model,
            messages=messages,  # full: system + history + user + tool results
            temperature=settings.default_temperature,
            max_tokens=settings.default_max_tokens,
            timeout=120,
            **direct_kwargs,
        )

        llm_text = full_resp.choices[0].message.content or ""

        elapsed_ms = int((time.perf_counter() - start) * 1000)"""

acompletion_new = """        direct_model, direct_kwargs = _resolve_direct_llm(model_name, api_key, settings)
        
        x_middlewares = state.get("x_middlewares", "[]")
        role = state.get("user_role", "customer")
        tool_schemas = get_llm_tool_schemas(x_middlewares, role)

        completion_kwargs = direct_kwargs.copy()
        if tool_schemas:
            # Strip parameter nesting artifacts if any 
            cleaned_schemas = []
            for t in tool_schemas:
                if "function" in t and "parameters" in t["function"]:
                    props = t["function"]["parameters"].get("properties", {})
                    # Ensure property shape is simple json schema
                    cleaned_schemas.append(t)
                else:
                    cleaned_schemas.append(t)
            
            completion_kwargs["tools"] = cleaned_schemas
            completion_kwargs["tool_choice"] = "auto"

        full_resp = await acompletion(
            model=direct_model,
            messages=messages,  # full: system + history + user + tool results
            temperature=settings.default_temperature,
            max_tokens=settings.default_max_tokens,
            timeout=120,
            **completion_kwargs,
        )

        message = full_resp.choices[0].message
        llm_text = message.content or ""
        
        tool_plan = []
        if getattr(message, "tool_calls", None):
            for tc in message.tool_calls:
                import json
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {}
                tool_plan.append({
                    "id": tc.id,
                    "tool": tc.function.name,
                    "args": args
                })

        elapsed_ms = int((time.perf_counter() - start) * 1000)"""

content = content.replace(acompletion_old, acompletion_new)

# UPDATE RETURN
return_old = """        return {
            **state,
            **token_state,
            "llm_messages": messages,
            "llm_response": llm_text,
            "firewall_decision": firewall_decision,
            "trace": trace.data,
        }"""
return_new = """        return {
            **state,
            **token_state,
            "llm_messages": messages,
            "llm_response": llm_text,
            "firewall_decision": firewall_decision,
            "tool_plan": tool_plan,
            "trace": trace.data,
        }"""
content = content.replace(return_old, return_new)

with open("apps/agent-demo/src/agent/nodes/llm_call.py", "w") as f:
    f.write(content)

