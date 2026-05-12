"""Tool registry utilities for internal and external tools."""

from __future__ import annotations

from typing import Any

from dotenv import load_dotenv

from agent_runtime.domain.rbac.service import get_rbac_service
from agent_runtime.domain.validation.schemas import TOOL_SCHEMAS
from agent_runtime.infrastructure.tools.commerce import (
    get_orders,
    get_users,
    search_products,
    update_order,
    update_user,
)

load_dotenv(".env")

from agent_runtime.infrastructure.tools.kb import search_knowledge_base  # noqa: E402
from agent_runtime.infrastructure.tools.orders import get_order_status  # noqa: E402
from agent_runtime.infrastructure.tools.secrets import get_internal_secrets  # noqa: E402

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
    "createSubAgent": "Create a new subagent under the current main agent and bind it for future delegation.",
}


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
    if tool_name == "createSubAgent":
        return {
            "type": "function",
            "function": {
                "name": "createSubAgent",
                "description": DEFAULT_TOOL_DESCRIPTIONS["createSubAgent"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Short subagent name."},
                        "description": {"type": "string", "description": "What this subagent is responsible for."},
                        "when_to_delegate": {
                            "type": "string",
                            "description": "When the main agent should delegate to this subagent.",
                        },
                        "delegation_description": {
                            "type": "string",
                            "description": "Short description shown in the delegation tool.",
                        },
                    },
                    "required": ["name", "description", "when_to_delegate"],
                },
            },
        }

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
