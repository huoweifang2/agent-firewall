"""Runtime tool protection helpers shared by pre/post gates."""

from __future__ import annotations

import json
from typing import Any, Literal

from agent_runtime.application.runtime_access import get_runtime_tool

GateName = Literal["pre", "post"]


def _middleware_protection(tool_name: str, x_middlewares: str) -> bool | None:
    try:
        middlewares = json.loads(x_middlewares or "[]")
    except Exception:
        return None

    if not isinstance(middlewares, list):
        return None

    for middleware in middlewares:
        if not isinstance(middleware, dict):
            continue
        app_prefix = str(middleware.get("name", "")).upper() + "_"
        if tool_name.upper().startswith(app_prefix):
            return bool(middleware.get("protected", False))
    return None


def is_tool_gate_enabled(
    tool_name: str,
    x_middlewares: str,
    runtime_spec: dict[str, Any] | None = None,
    *,
    gate: GateName,
) -> bool:
    """Return whether the named runtime gate should protect this tool.

    Runtime specs are authoritative when they define a gate flag. Middleware
    metadata is the compatibility fallback for external app-prefixed tools.
    Unknown tools default to protected.
    """
    tool_spec = get_runtime_tool(runtime_spec, tool_name)
    flag_key = f"{gate}_gate_enabled"
    if isinstance(tool_spec, dict) and isinstance(tool_spec.get(flag_key), bool):
        return bool(tool_spec[flag_key])

    middleware_value = _middleware_protection(tool_name, x_middlewares)
    if middleware_value is not None:
        return middleware_value

    return True
