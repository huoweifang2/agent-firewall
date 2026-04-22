"""Tool registry utilities for internal and Composio-backed tools."""

from __future__ import annotations

import json
import os
from typing import Any

import structlog
from dotenv import load_dotenv

from src.agent.rbac.service import get_rbac_service
from src.agent.tools.commerce import get_orders, get_users, search_products, update_order, update_user
from src.agent.validation.schemas import TOOL_SCHEMAS

load_dotenv(".env")

from src.agent.tools.kb import search_knowledge_base  # noqa: E402
from src.agent.tools.orders import get_order_status  # noqa: E402
from src.agent.tools.secrets import get_internal_secrets  # noqa: E402

try:
    from ddgs import DDGS

    def web_search(query: str) -> str:
        try:
            results = DDGS().text(query, max_results=3)
            if not results:
                return "No results found."
            return "\n\n".join(
                [f"Title: {r.get('title')}\nURL: {r.get('href')}\nSnippet: {r.get('body')}" for r in results]
            )
        except Exception as exc:
            return f"Search failed: {str(exc)}"
except ImportError:

    def web_search(query: str) -> str:
        return "DuckDuckGo search library is not installed."


logger = structlog.get_logger()

TOOL_FUNCTIONS = {
    "searchKnowledgeBase": search_knowledge_base,
    "getOrderStatus": get_order_status,
    "getInternalSecrets": get_internal_secrets,
    "getOrders": get_orders,
    "getUsers": get_users,
    "searchProducts": search_products,
    "updateOrder": update_order,
    "updateUser": update_user,
    "WEB_SEARCH": web_search,
}

DEFAULT_TOOL_DESCRIPTIONS = {
    "searchKnowledgeBase": "Search the knowledge base / FAQ for information.",
    "getOrderStatus": "Look up order status by order ID.",
    "getInternalSecrets": "Retrieve internal API keys and configuration. No args needed.",
    "getOrders": "List known orders or inspect a specific order by ID.",
    "getUsers": "List users and their profile details.",
    "searchProducts": "Search products by name or category.",
    "updateOrder": "Update an order status.",
    "updateUser": "Update a user profile field.",
    "WEB_SEARCH": "Search the web for real-time information and URLs using DuckDuckGo.",
}

composio_client = None
try:
    if os.environ.get("COMPOSIO_API_KEY"):
        from composio import Composio

        composio_client = Composio(api_key=os.environ.get("COMPOSIO_API_KEY"))
except ImportError:
    pass
except Exception as exc:
    logger.warning("composio_init_failed", error=str(exc))


def get_internal_tool_names() -> list[str]:
    return list(TOOL_FUNCTIONS.keys())


def get_allowed_tools(role_name: str) -> list[str]:
    """Backward-compatible RBAC helper used by legacy tests and nodes."""
    return get_rbac_service().get_allowed_tools(role_name)


def execute_internal_tool(tool_name: str, args: dict[str, Any]) -> str:
    if tool_name not in TOOL_FUNCTIONS:
        raise ValueError(f"Internal tool '{tool_name}' is not registered")
    return TOOL_FUNCTIONS[tool_name](**args)


def get_internal_tool_schema(tool_name: str) -> dict[str, Any] | None:
    schema_cls = TOOL_SCHEMAS.get(tool_name)
    if schema_cls is not None:
        schema = schema_cls.model_json_schema()
        return {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": DEFAULT_TOOL_DESCRIPTIONS.get(tool_name, tool_name),
                "parameters": schema,
            },
        }

    if tool_name == "WEB_SEARCH":
        return {
            "type": "function",
            "function": {
                "name": "WEB_SEARCH",
                "description": DEFAULT_TOOL_DESCRIPTIONS["WEB_SEARCH"],
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "Search query string"}},
                    "required": ["query"],
                },
            },
        }

    return None


def get_internal_tool_schemas(tool_names: list[str]) -> list[dict[str, Any]]:
    schemas: list[dict[str, Any]] = []
    for tool_name in tool_names:
        schema = get_internal_tool_schema(tool_name)
        if schema is not None:
            schemas.append(schema)
    return schemas


def get_tools_description(tool_names: list[str]) -> str:
    lines: list[str] = []
    for tool_name in tool_names:
        description = DEFAULT_TOOL_DESCRIPTIONS.get(tool_name, tool_name)
        lines.append(f"- {tool_name}: {description}")
    return "\n".join(lines)


def fetch_composio_schemas(app_refs: list[str], user_id: str = "default_user") -> list[dict[str, Any]]:
    if composio_client is None or not app_refs:
        return []
    try:
        app_slugs = [app.lower() for app in app_refs]
        session = composio_client.create(user_id=user_id, toolkits=app_slugs, manage_connections=True)
        return list(session.tools())
    except Exception as exc:
        logger.error("composio_fetch_schema_error", error=str(exc))
        return []


def execute_composio_tool(
    tool_name: str,
    args: dict[str, Any],
    *,
    user_id: str = "default_user",
    app_refs: list[str] | None = None,
) -> str:
    if composio_client is None:
        return f"Error executing tool {tool_name}: Composio SDK not initialized."

    try:
        slugs = [app.lower() for app in (app_refs or [])]
        session = composio_client.create(user_id=user_id, toolkits=slugs, manage_connections=True)

        if tool_name == "COMPOSIO_MANAGE_CONNECTIONS":
            toolkits_to_auth = args.get("toolkits", args.get("expected_toolkits", slugs))
            if not toolkits_to_auth:
                return "Please specify which toolkit you want to connect (e.g. 'github')."
            slug = toolkits_to_auth[0].lower()
            conn_request = session.authorize(slug)
            return (
                f"Action required: Please click this link to authorize {slug.upper()}: "
                f"{conn_request.redirect_url}\nOnce you are done, just confirm with me here!"
            )

        if hasattr(session, "execute"):
            response = session.execute(tool_slug=tool_name, arguments=args)
        else:
            response = session.execute_action(action=tool_name, params=args)

        if hasattr(response, "model_dump_json"):
            return response.model_dump_json()
        if hasattr(response, "json"):
            return response.json()
        return str(response)
    except Exception as exc:
        logger.error("composio_execute_error", tool=tool_name, error=str(exc))
        return f"Error executing Composio tool {tool_name}: {str(exc)}"


def normalize_external_tool_schema(tool_name: str, tool_spec: dict[str, Any]) -> dict[str, Any]:
    arg_schema = tool_spec.get("arg_schema")
    if isinstance(arg_schema, dict) and arg_schema.get("type") == "function" and "function" in arg_schema:
        schema = dict(arg_schema)
        schema["function"] = dict(schema["function"])
        schema["function"]["name"] = tool_name
        return schema

    provider = arg_schema.get("provider") if isinstance(arg_schema, dict) else None
    properties = {}
    required: list[str] = []
    if isinstance(provider, dict):
        props = provider.get("properties")
        if isinstance(props, dict):
            properties = props
        req = provider.get("required")
        if isinstance(req, list):
            required = [str(item) for item in req]

    return {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": tool_spec.get("description", tool_name),
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def describe_external_tool(tool_spec: dict[str, Any]) -> str:
    provider_type = tool_spec.get("provider_type", "external")
    description = tool_spec.get("description", "")
    return f"{provider_type}: {description}".strip()


def parse_app_refs(tool_spec: dict[str, Any]) -> list[str]:
    arg_schema = tool_spec.get("arg_schema")
    provider = arg_schema.get("provider") if isinstance(arg_schema, dict) else None
    if not isinstance(provider, dict):
        return []
    app_refs = provider.get("apps") or provider.get("toolkits") or []
    if isinstance(app_refs, list):
        return [str(item) for item in app_refs]
    if isinstance(app_refs, str) and app_refs:
        return [app_refs]
    provider_ref = provider.get("ref")
    if isinstance(provider_ref, str) and provider_ref:
        return [provider_ref]
    return []
