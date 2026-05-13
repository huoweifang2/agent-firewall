"""Helpers for reading runtime-spec data inside the agent runtime."""

from __future__ import annotations

import re
from typing import Any

from agent_runtime.domain.rbac.service import get_rbac_service
from agent_runtime.domain.state import AgentState


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug or "agent"


def get_runtime_spec(state: AgentState) -> dict[str, Any] | None:
    return state.get("runtime_spec")


def resolve_effective_role(requested_role: str | None, runtime_spec: dict[str, Any] | None) -> str:
    if runtime_spec is None:
        return requested_role or "customer"
    role_names = [role.get("name", "") for role in runtime_spec.get("roles", [])]
    if requested_role:
        if requested_role in role_names:
            return requested_role
        return requested_role
    default_role = runtime_spec.get("default_role")
    if isinstance(default_role, str) and default_role:
        return default_role
    if role_names:
        return role_names[0]
    return requested_role or "customer"


def get_role_spec(runtime_spec: dict[str, Any] | None, role_name: str) -> dict[str, Any] | None:
    if runtime_spec is None:
        return None
    for role in runtime_spec.get("roles", []):
        if role.get("name") == role_name:
            return role
    return None


def get_allowed_tools_for_role(runtime_spec: dict[str, Any] | None, role_name: str) -> list[str]:
    if runtime_spec is None:
        return get_rbac_service().get_allowed_tools(role_name)
    role = get_role_spec(runtime_spec, role_name)
    if role is None:
        return []
    tools = list(role.get("effective_tools", []))
    if runtime_spec.get("agent_kind") == "main_agent":
        tools.append("createSubAgent")
    tools.extend(get_delegate_tool_names(runtime_spec))
    return sorted(dict.fromkeys(tools))


def role_can_use_tool(runtime_spec: dict[str, Any] | None, role_name: str, tool_name: str) -> dict[str, Any]:
    if runtime_spec is None:
        result = get_rbac_service().check_permission(role_name, tool_name)
        return {
            "allowed": result.allowed,
            "decision": "confirm" if result.requires_confirmation else ("allow" if result.allowed else "deny"),
            "reason": result.reason,
            "requires_confirmation": result.requires_confirmation,
            "tool_sensitivity": result.tool_sensitivity,
            "scopes_granted": list(result.scopes_granted),
        }

    if tool_name == "createSubAgent" and runtime_spec.get("agent_kind") == "main_agent":
        return {
            "allowed": True,
            "decision": "allow",
            "reason": "Main agents may create subagents in the sandbox.",
            "requires_confirmation": False,
            "tool_sensitivity": "medium",
            "scopes_granted": ["create", "delegate"],
        }

    if is_delegate_tool_name(runtime_spec, tool_name):
        return {
            "allowed": True,
            "decision": "allow",
            "reason": f"Delegation tool '{tool_name}' is available to the runtime.",
            "requires_confirmation": False,
            "tool_sensitivity": "medium",
            "scopes_granted": ["delegate"],
        }

    role = get_role_spec(runtime_spec, role_name)
    if role is None:
        return {
            "allowed": False,
            "decision": "deny",
            "reason": f"Unknown role: '{role_name}'",
            "requires_confirmation": False,
            "tool_sensitivity": "low",
            "scopes_granted": [],
        }

    for permission in role.get("permissions", []):
        if permission.get("tool_name") == tool_name:
            return {
                "allowed": True,
                "decision": permission.get("decision", "allow"),
                "reason": f"Role '{role_name}' may use '{tool_name}'",
                "requires_confirmation": bool(permission.get("requires_confirmation", False)),
                "tool_sensitivity": permission.get("sensitivity", "low"),
                "scopes_granted": permission.get("scopes", []),
            }

    return {
        "allowed": False,
        "decision": "deny",
        "reason": f"Tool '{tool_name}' not in allowlist for role '{role_name}'",
        "requires_confirmation": False,
        "tool_sensitivity": "low",
        "scopes_granted": [],
    }


def get_runtime_tool(runtime_spec: dict[str, Any] | None, tool_name: str) -> dict[str, Any] | None:
    if tool_name == "createSubAgent":
        return {
            "name": "createSubAgent",
            "description": "Create and bind a new subagent under the current main agent.",
            "provider_type": "internal",
            "provider_ref": "createSubAgent",
            "access_type": "write",
            "sensitivity": "medium",
            "requires_confirmation": False,
            "arg_schema": None,
            "returns_pii": False,
            "returns_secrets": False,
            "pre_gate_enabled": True,
            "post_gate_enabled": True,
            "rate_limit": None,
        }
    if runtime_spec is None:
        return None
    for tool in runtime_spec.get("tools", []):
        if tool.get("name") == tool_name:
            return tool
    return None


def get_runtime_tools(runtime_spec: dict[str, Any] | None) -> list[dict[str, Any]]:
    if runtime_spec is None:
        return []
    return list(runtime_spec.get("tools", []))


def get_runtime_skills(runtime_spec: dict[str, Any] | None, *, scopes: set[str] | None = None) -> list[dict[str, Any]]:
    if runtime_spec is None:
        return []
    skills = list(runtime_spec.get("skills", []))
    if scopes is None:
        return skills
    return [skill for skill in skills if skill.get("scope") in scopes]


def get_runtime_sub_agents(runtime_spec: dict[str, Any] | None) -> list[dict[str, Any]]:
    if runtime_spec is None:
        return []
    return list(runtime_spec.get("sub_agents", []))


def delegation_tool_name(sub_agent: dict[str, Any]) -> str:
    return f"delegate_to_{_slugify(str(sub_agent.get('name', 'agent')))}"


def get_delegate_tool_names(runtime_spec: dict[str, Any] | None) -> list[str]:
    return [delegation_tool_name(sub_agent) for sub_agent in get_runtime_sub_agents(runtime_spec)]


def is_delegate_tool_name(runtime_spec: dict[str, Any] | None, tool_name: str) -> bool:
    return tool_name in get_delegate_tool_names(runtime_spec)


def get_sub_agent_by_delegate_tool(runtime_spec: dict[str, Any] | None, tool_name: str) -> dict[str, Any] | None:
    for sub_agent in get_runtime_sub_agents(runtime_spec):
        if delegation_tool_name(sub_agent) == tool_name:
            return sub_agent
    return None
