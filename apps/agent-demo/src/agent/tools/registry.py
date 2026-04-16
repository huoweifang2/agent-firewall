"""Tool registry — tool dispatch and descriptions using Composio SDK."""

from __future__ import annotations

import json
from typing import Any
import structlog
import os
from dotenv import load_dotenv

# Ensure environment variables are loaded so os.environ.get sees COMPOSIO_API_KEY
load_dotenv(".env")

from src.agent.rbac.service import get_rbac_service
from src.agent.tools.kb import search_knowledge_base
from src.agent.tools.orders import get_order_status
from src.agent.tools.secrets import get_internal_secrets

try:
    from ddgs import DDGS
    def web_search(query: str) -> str:
        try:
            results = DDGS().text(query, max_results=3)
            if not results:
                return "No results found."
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
        # Initialize global Composio SDK correctly via Composio
        from composio import Composio
        composio_client = Composio(api_key=os.environ.get("COMPOSIO_API_KEY"))
except ImportError:
    pass
except Exception as e:
    logger.warning("composio_init_failed", error=str(e))

def get_tools_description(allowed_tools: list[str]) -> str:
    return "- WEB_SEARCH: Search the web for real-time information\n- Composio: Execute 100+ integrations dynamically"

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

def get_llm_tool_schemas(x_middlewares: str | None, user_role: str, user_id: str = "default_user") -> list[dict]:
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

    # Convert generic schemas to Composio integrations
    if composio_client and apps:
        try:
            # Lowercase for the new API 
            app_slugs = [a.lower() for a in apps if a != "WEB_SEARCH"]
            if app_slugs:
                session = composio_client.create(user_id=user_id, toolkits=app_slugs, manage_connections=True)
                composio_tools = session.tools(provider="openai")
                # Composio returns a list of openai tool schema objects: {"type": "function", "function": {...}}
                schemas.extend(composio_tools)
        except Exception as e:
            logger.error("composio_fetch_schema_error", error=str(e))

    return schemas

def execute_tool(tool_name: str, args: dict[str, Any], user_id: str = "default_user", apps: list[str] = None) -> str:
    if tool_name in TOOL_FUNCTIONS:
        return TOOL_FUNCTIONS[tool_name](**args)
        
    # Execute Composio natively!
    if composio_client:
        try:
            if not apps:
                apps = []
            app_slugs = [a.lower() for a in apps if a != "WEB_SEARCH"]
            session = composio_client.create(user_id=user_id, toolkits=app_slugs, manage_connections=True)
            # execute via session
            # Composio v0.11+ session objects handle execution directly or you can execute via the client
            # The exact method might vary, but standard pattern is session.execute_action(action=tool_name, params=args)
            if hasattr(session, "execute_action"):
                result = session.execute_action(action=tool_name, params=args)
            else:
                # App fallback for direct execute if session execute doesn't exist
                result = composio_client.execute_action(action=tool_name, params=args, user_id=user_id)
            return str(result)
        except Exception as e:
            logger.error("composio_execute_error", tool=tool_name, error=str(e))
            return f"Error executing Composio tool {tool_name}: {str(e)}"
            
    return f"Error executing tool {tool_name}: Not found or Composio SDK not initialized."
