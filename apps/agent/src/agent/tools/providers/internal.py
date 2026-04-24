"""Internal tool provider."""

from __future__ import annotations

from typing import Any

from src.agent.tools.registry import execute_internal_tool


async def execute(tool_name: str, args: dict[str, Any]) -> str:
    return execute_internal_tool(tool_name, args)
