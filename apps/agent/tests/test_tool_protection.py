"""Tests for shared runtime tool protection helper."""

from __future__ import annotations

from agent_runtime.application.runtime.tool_protection import is_tool_gate_enabled


def test_runtime_spec_pre_gate_flag_overrides_middleware() -> None:
    runtime_spec = {
        "tools": [
            {
                "name": "ASANA_create_task",
                "pre_gate_enabled": False,
                "post_gate_enabled": True,
            }
        ]
    }

    enabled = is_tool_gate_enabled(
        "ASANA_create_task",
        '[{"name":"ASANA","protected":true}]',
        runtime_spec,
        gate="pre",
    )

    assert enabled is False


def test_runtime_spec_post_gate_flag_is_independent() -> None:
    runtime_spec = {
        "tools": [
            {
                "name": "openclaw_weather",
                "pre_gate_enabled": True,
                "post_gate_enabled": False,
            }
        ]
    }

    assert is_tool_gate_enabled("openclaw_weather", "[]", runtime_spec, gate="pre") is True
    assert is_tool_gate_enabled("openclaw_weather", "[]", runtime_spec, gate="post") is False


def test_middleware_prefix_controls_external_tools_when_runtime_spec_missing() -> None:
    enabled = is_tool_gate_enabled(
        "ASANA_create_task",
        '[{"name":"ASANA","protected":false}]',
        None,
        gate="pre",
    )

    assert enabled is False


def test_unknown_or_invalid_middleware_defaults_to_protected() -> None:
    assert is_tool_gate_enabled("unknownTool", "not-json", None, gate="post") is True
    assert is_tool_gate_enabled("unknownTool", "[]", None, gate="post") is True
