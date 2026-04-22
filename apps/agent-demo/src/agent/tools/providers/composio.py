"""Composio tool provider."""

from __future__ import annotations

from typing import Any

from src.agent.tools.registry import execute_composio_tool


async def execute(tool_name: str, args: dict[str, Any], *, user_id: str, app_refs: list[str] | None = None) -> str:
    return execute_composio_tool(tool_name, args, user_id=user_id, app_refs=app_refs)
