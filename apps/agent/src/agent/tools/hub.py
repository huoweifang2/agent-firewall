"""Unified tool execution hub."""

from __future__ import annotations

from typing import Any

from src.agent.runtime_access import get_runtime_tool, get_sub_agent_by_delegate_tool, is_delegate_tool_name
from src.agent.subagents import create_sub_agent_from_runtime, run_sub_agent
from src.agent.tools.providers import internal as internal_provider
from src.agent.tools.providers import mcp as mcp_provider
from src.agent.tools.providers import openclaw as openclaw_provider


async def execute_tool_call(state: dict[str, Any], tool_name: str, args: dict[str, Any]) -> str:
    runtime_spec = state.get("runtime_spec")
    if tool_name == "createSubAgent":
        return await create_sub_agent_from_runtime(
            parent_state=state,
            name=str(args.get("name", "")).strip() or "New Subagent",
            description=str(args.get("description", "")).strip(),
            when_to_delegate=str(args.get("when_to_delegate", "")).strip(),
            delegation_description=str(args.get("delegation_description", "")).strip(),
        )

    if is_delegate_tool_name(runtime_spec, tool_name):
        sub_agent = get_sub_agent_by_delegate_tool(runtime_spec, tool_name)
        if sub_agent is None:
            return f"Delegation target for {tool_name} was not found."
        task = str(args.get("task", "")).strip()
        if not task:
            return f"Delegation to {sub_agent.get('name', 'sub-agent')} requires a task."
        return await run_sub_agent(parent_state=state, child_agent_id=str(sub_agent["agent_id"]), task=task)

    tool_spec = get_runtime_tool(runtime_spec, tool_name)
    provider_type = tool_spec.get("provider_type") if isinstance(tool_spec, dict) else None
    if provider_type == "openclaw":
        return await openclaw_provider.execute(
            tool_name,
            args,
            tool_spec=tool_spec,
            session_id=state.get("session_id", "default_user"),
            original_request=state.get("message", ""),
        )
    if provider_type == "mcp":
        provider = None
        if isinstance(tool_spec, dict):
            arg_schema = tool_spec.get("arg_schema")
            provider = arg_schema.get("provider") if isinstance(arg_schema, dict) else None
        return await mcp_provider.execute(tool_name, args, provider=provider)

    return await internal_provider.execute(tool_name, args)
