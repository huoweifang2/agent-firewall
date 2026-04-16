"""Tool registry — tool dispatch and descriptions using Composio SDK."""

from __future__ import annotations

import json
from typing import Any
import structlog
import os

from src.agent.rbac.service import get_rbac_service
from src.agent.tools.kb import search_knowledge_base
from src.agent.tools.orders import get_order_status
from src.agent.tools.secrets import get_internal_secrets

try:
    from duckduckgo_search import DDGS
    # Function to grab some live duckduckgo results
    def web_search(query: str) -> str:
        try:
            results = DDGS().text(query, max_results=3)
            if not results:
                return "No results found."
            # format the results
            return "\n\n".join([f"Title: {r.get('title')}\nURL: {r.get('href')}\nSnippet: {r.get('body')}" for r in results])
        except Exception as e:
            return f"Search failed: {str(e)}"
except ImportError:
    def web_search(query: str) -> str:
        return "Duckduckgo search library is not installed."


logger = structlog.get_logger()

TOOL_FUNCTIONS = {
    "searchKnowledgeBase": search_knowledge_base,
    "getOrderStatus": get_order_status,
    "getInternalSecrets": get_internal_secrets,
    "WEB_SEARCH": web_search,
}

composio_client = None
try:
    if os.environ.get("COMPOSIO_API_KEY"):
        # Initialize global Composio client if API Key is configured
        from composio import Composio
        composio_client = Composio(api_key=os.environ.get("COMPOSIO_API_KEY"))
except ImportError:
    pass
except Exception as e:
    logger.warning("composio_init_failed", error=str(e))


def get_tools_description(allowed_tools: list[str]) -> str:
    # We no longer strictly list allowed tools here since we dynamically fetch schemas and LLMs use schemas.
    # Just return a generic note.
    return "You have access to the dynamic tools provided in the API tools schema array."

def get_allowed_tools(user_role: str) -> list[str]:
    return []

def get_active_composio_apps(x_middlewares: str | None) -> list[str]:
    if not x_middlewares:
        return []
    try:
        middlewares = json.loads(x_middlewares)
        return [m["name"].upper() for m in middlewares if m.get("enabled")]
    except Exception:
        return []

def get_llm_tool_schemas(x_middlewares: str | None, user_role: str) -> list[dict]:
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

    # In Advanced Session Mode, if composio is installed and an API key is available,
    # we return the dynamic meta tools (COMPOSIO_SEARCH_TOOLS, COMPOSIO_MANAGE_CONNECTIONS, etc.)
    if composio_client:
        try:
            # We use a default playground_user for the demo context.
            # In a real system, you'd extract the user ID from the request state.
            session = composio_client.create(user_id="playground_user")
            
            # Fetch the meta tools for LLM use
            # Depending on the SDK bindings, this returns schema objects.
            # Convert them to raw dicts if required by LiteLLM:
            meta_tools = session.tools()
            for tool in meta_tools:
                if hasattr(tool, "model_dump"):
                    schemas.append({"type": "function", "function": tool.model_dump()})
                elif hasattr(tool, "to_openai_tool"):
                    schemas.append(tool.to_openai_tool())
                elif isinstance(tool, dict):
                    schemas.append(tool)
                else:
                    # Generic fallback based on arbitrary SDK objects
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
            logger.error("composio_session_tools_error", error=str(e))
    
    # Fallback mock for weather if we don't have composio running
    apps = get_active_composio_apps(x_middlewares)
    
    if "WEB_SEARCH" in apps:
             schemas.append({
                 "type": "function",
                 "function": {
                     "name": "WEB_SEARCH",
                     "description": "Search the web for real-time information and URLs using DuckDuckGo.",
                     "parameters": {
                         "type": "object",
                         "properties": {
                             "query": {"type": "string", "description": "Search query string"}
                         },
                         "required": ["query"]
                     }
                 }
             })

    if apps and not composio_client:
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

    return schemas

def execute_tool(tool_name: str, args: dict[str, Any]) -> str:
    if tool_name in TOOL_FUNCTIONS:
        return TOOL_FUNCTIONS[tool_name](**args)
        
    if tool_name == "WEATHERMAP_WEATHER":
        city = args.get("q", "Unknown")
        return f"The current weather in {city} is sunny, 24°C (Mocked response due to missing COMPOSIO_API_KEY)."

    if composio_client and tool_name.startswith("COMPOSIO_"):
        try:
            # Recreate session (or store session context in state)
            session = composio_client.create(user_id="playground_user")
            
            # Execute the specific meta-tool (like COMPOSIO_SEARCH_TOOLS or COMPOSIO_MULTI_EXECUTE_TOOL)
            result = composio_client.tools.execute(
                name=tool_name,
                user_id="playground_user",
                arguments=args
            )
            return str(result)
        except Exception as e:
            logger.error("composio_meta_tool_error", tool=tool_name, error=str(e))
            return f"Error executing Composio Session tool {tool_name}: {str(e)}"
            
    return f"Error executing tool {tool_name}: Composio SDK not initialized."
