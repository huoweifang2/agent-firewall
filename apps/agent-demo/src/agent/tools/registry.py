"""Tool registry — tool dispatch and descriptions using Composio SDK."""

from __future__ import annotations

import json
from typing import Any
import structlog
from composio import ComposioToolSet, Action, App

from src.agent.rbac.service import get_rbac_service
from src.agent.tools.kb import search_knowledge_base
from src.agent.tools.orders import get_order_status
from src.agent.tools.secrets import get_internal_secrets

logger = structlog.get_logger()

# Our internal local tools if needed
TOOL_FUNCTIONS = {
    "searchKnowledgeBase": search_knowledge_base,
    "getOrderStatus": get_order_status,
    "getInternalSecrets": get_internal_secrets,
}

tool_set = ComposioToolSet()

def get_allowed_tools(user_role: str) -> list[str]:
    """Return list of allowed tools (internal apps + composio)."""
    # For simplicity of the agent, let's load all apps user configured via 'Middleware' config
    # In a real app we'd intersect these with rbac.
    return []

def get_active_composio_apps(x_middlewares: str | None) -> list[str]:
    """Decode frontend's x-middlewares JSON to get active tools."""
    if not x_middlewares:
        return []
    try:
        middlewares = json.loads(x_middlewares)
        active_apps = [m["name"].upper() for m in middlewares if m.get("enabled")]
        return active_apps
    except Exception:
        return []

def get_llm_tool_schemas(x_middlewares: str | None, user_role: str) -> list[dict]:
    """Format local tools + enabled composio tools into OpenAI function calling format."""
    schemas = []
    schemas.extend([
        {
            "type": "function",
            "function": {
                "name": "searchKnowledgeBase",
                "description": "Search the knowledge base / FAQ for information.",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "getOrderStatus",
                "description": "Look up order status by order ID.",
                "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "getInternalSecrets",
                "description": "Retrieve internal API keys and configuration. No args needed.",
                "parameters": {"type": "object", "properties": {}}
            }
        }
    ])

    apps = get_active_composio_apps(x_middlewares)
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
            
    return schemas

def execute_tool(tool_name: str, args: dict[str, Any]) -> str:
    """Execute a tool by name with given args using local or Composio SDK."""
    if tool_name in TOOL_FUNCTIONS:
        return TOOL_FUNCTIONS[tool_name](**args)
        
    try:
        result = tool_set.execute_action(action=tool_name, params=args)
        return str(result)
    except Exception as e:
        logger.error("composio_tool_execution_error", tool=tool_name, error=str(e))
        return f"Error executing tool {tool_name}: {str(e)}"
