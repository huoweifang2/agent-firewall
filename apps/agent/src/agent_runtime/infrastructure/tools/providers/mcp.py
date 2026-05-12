"""MCP tool provider.

Current implementation accepts declarative HTTP-style provider metadata in
tool.arg_schema.provider. This gives the runtime a stable provider slot now,
while allowing real MCP transport integration later without changing the
runtime contracts.
"""

from __future__ import annotations

from typing import Any

import httpx


async def execute(tool_name: str, args: dict[str, Any], *, provider: dict[str, Any] | None = None) -> str:
    if not isinstance(provider, dict):
        return f"Error executing MCP tool {tool_name}: missing provider config."

    mock_result = provider.get("mock_result")
    if isinstance(mock_result, str) and mock_result:
        return mock_result

    endpoint = provider.get("endpoint")
    if not isinstance(endpoint, str) or not endpoint:
        return f"Error executing MCP tool {tool_name}: provider.endpoint is required."

    method = str(provider.get("method", "POST")).upper()
    headers = provider.get("headers") if isinstance(provider.get("headers"), dict) else {}
    payload = {"tool": tool_name, "arguments": args}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(method, endpoint, json=payload, headers=headers)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        return response.text
    return response.text
