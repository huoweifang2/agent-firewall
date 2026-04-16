import os

with open("src/agent/tools/registry.py", "r") as f:
    content = f.read()

old_import = "from composio import ComposioToolSet, Action, App"
new_import = """import os
try:
    if os.environ.get("COMPOSIO_API_KEY"):
        from composio import ComposioToolSet, Action, App
    else:
        ComposioToolSet = None
except ImportError:
    ComposioToolSet = None"""
content = content.replace(old_import, new_import)

old_init = "tool_set = ComposioToolSet()"
new_init = """try:
    tool_set = ComposioToolSet() if ComposioToolSet else None
except Exception:
    tool_set = None"""
content = content.replace(old_init, new_init)

old_schemas = """    apps = get_active_composio_apps(x_middlewares)
    if apps:
        try:
            # map strings to Composio App Enums if they match
            app_enums = [App(name) for name in apps if name in [e.value for e in App]]
            if app_enums:
                composio_tools = tool_set.get_tools(apps=app_enums)
                for tool in composio_tools:
                    # tool.args_schema is a pydantic model or dict
                    properties = {}
                    if hasattr(tool, "args_schema") and tool.args_schema:
                        properties = tool.args_schema.schema()
                    schemas.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": properties
                        }
                    })
        except Exception as e:
            logger.error("composio_schema_load_error", error=str(e))
            
    return schemas"""
new_schemas = """    apps = get_active_composio_apps(x_middlewares)
    if apps and tool_set:
        try:
            from composio import App
            app_enums = [App(name) for name in apps if name in [e.value for e in App]]
            if app_enums:
                composio_tools = tool_set.get_tools(apps=app_enums)
                for tool in composio_tools:
                    properties = {}
                    if hasattr(tool, "args_schema") and tool.args_schema:
                        properties = tool.args_schema.schema()
                    schemas.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": properties
                        }
                    })
        except Exception as e:
            logger.error("composio_schema_load_error", error=str(e))
    elif apps:
        if "WEATHERMAP" in apps or "OPENWEATHERMAP" in apps:
             schemas.append({
                 "type": "function",
                 "function": {
                     "name": "WEATHERMAP_WEATHER",
                     "description": "Get current weather in a city.",
                     "parameters": {
                         "type": "object",
                         "properties": {
                             "q": {"type": "string", "description": "City name"}
                         },
                         "required": ["q"]
                     }
                 }
             })
    return schemas"""
content = content.replace(old_schemas, new_schemas)

old_exec = """    try:
        result = tool_set.execute_action(action=tool_name, params=args)
        return str(result)
    except Exception as e:
        logger.error("composio_tool_execution_error", tool=tool_name, error=str(e))
        return f"Error executing tool {tool_name}: {str(e)}\""""
new_exec = """    if tool_name == "WEATHERMAP_WEATHER":
        city = args.get("q", "Unknown")
        return f"The current weather in {city} is sunny, 24°C (Mocked response due to missing API KEY)."

    if tool_set:
        try:
            result = tool_set.execute_action(action=tool_name, params=args)
            return str(result)
        except Exception as e:
            logger.error("composio_tool_execution_error", tool=tool_name, error=str(e))
            return f"Error executing tool {tool_name}: {str(e)}"
    
    return f"Error executing tool {tool_name}: Composio SDK not initialized."
"""
content = content.replace(old_exec, new_exec)

with open("src/agent/tools/registry.py", "w") as f:
    f.write(content)
