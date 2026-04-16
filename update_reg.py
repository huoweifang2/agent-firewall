import re

with open("apps/agent-demo/src/agent/tools/registry.py", "r") as f:
    content = f.read()

func_old = """import structlog
from composio import ComposioToolSet, Action, App

from src.agent.rbac.service import get_rbac_service"""

func_new = """import structlog
import os

from src.agent.rbac.service import get_rbac_service"""

content = content.replace(func_old, func_new)

init_old = """tool_set = ComposioToolSet()"""

init_new = """tool_set = None
try:
    if os.environ.get("COMPOSIO_API_KEY"):
        from composio import ComposioToolSet, Action, App
        tool_set = ComposioToolSet()
except Exception as e:
    logger.warning("composio_init_failed", error=str(e))"""

content = content.replace(init_old, init_new)

schema_old = """    apps = get_active_composio_apps(x_middlewares)
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

schema_new = """    apps = get_active_composio_apps(x_middlewares)
    
    if apps and tool_set:
        try:
            # Try dynamic load
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
        # Mock WEATHERMAP if tool_set failed to load (e.g. no API KEY)
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

content = content.replace(schema_old, schema_new)

exec_old = """    try:
        result = tool_set.execute_action(action=tool_name, params=args)
        return str(result)
    except Exception as e:
        logger.error("composio_tool_execution_error", tool=tool_name, error=str(e))
        return f"Error executing tool {tool_name}: {str(e)}\""""

exec_new = """    if tool_name == "WEATHERMAP_WEATHER":
        city = args.get("q", "Unknown")
        return f"The current weather in {city} is sunny, 24°C (Mocked response)."

    if tool_set:
        try:
            result = tool_set.execute_action(action=tool_name, params=args)
            return str(result)
        except Exception as e:
            logger.error("composio_tool_execution_error", tool=tool_name, error=str(e))
            return f"Error executing tool {tool_name}: {str(e)}"
            
    return f"Error executing tool {tool_name}: Composio SDK not initialized. Missing COMPOSIO_API_KEY.\""""

content = content.replace(exec_old, exec_new)

with open("apps/agent-demo/src/agent/tools/registry.py", "w") as f:
    f.write(content)
