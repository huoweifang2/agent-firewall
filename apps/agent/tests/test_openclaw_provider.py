from __future__ import annotations

import types

import pytest

from src.agent.nodes.llm_call import _build_runtime_tool_schemas
from src.agent.openclaw_client import OpenClawClient, extract_json_payload
from src.agent.tools.hub import execute_tool_call
from src.agent.tools.providers import openclaw


class FakeProcess:
    def __init__(self, *, stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0):
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode
        self.killed = False

    async def communicate(self):
        return self._stdout, self._stderr

    def kill(self):
        self.killed = True


def _settings(**overrides):
    data = {
        "openclaw_bin": "openclaw",
        "openclaw_agent_id": "coder",
        "openclaw_agent_local": False,
        "openclaw_timeout_seconds": 30,
        "openclaw_plugin_stage_dir": "",
    }
    data.update(overrides)
    return types.SimpleNamespace(**data)


def test_derive_session_id_is_stable_and_namespaced():
    first = openclaw.derive_session_id("session 1", "openclaw_weather")
    second = openclaw.derive_session_id("session 1", "openclaw_weather")
    other = openclaw.derive_session_id("session 1", "openclaw_github")

    assert first == second
    assert first.startswith("agent-firewall-session-1-")
    assert first != other


def test_extract_json_payload_tolerates_banner_text():
    payload = extract_json_payload('OpenClaw ready\n{"response":"ok"}\n')
    assert payload == {"response": "ok"}


@pytest.mark.asyncio
async def test_agent_message_tolerates_plugin_logs_and_sets_stage_dir(monkeypatch, tmp_path):
    seen_env: dict[str, str] = {}

    async def fake_exec(*command, stdout=None, stderr=None, env=None):
        seen_env.update(env or {})
        return FakeProcess(stdout=b'[plugins] installed deps\n{"response":"ok"}')

    import src.agent.openclaw_client as client_mod

    monkeypatch.delenv("OPENCLAW_PLUGIN_STAGE_DIR", raising=False)
    monkeypatch.setattr(client_mod.asyncio, "create_subprocess_exec", fake_exec)
    client = OpenClawClient(plugin_stage_dir=str(tmp_path / "plugin-runtime"))

    payload = await client.agent_message(message="hello", session_id="s1", agent_id="coder")

    assert payload == {"response": "ok"}
    assert seen_env["OPENCLAW_PLUGIN_STAGE_DIR"] == str(tmp_path / "plugin-runtime")


def test_openclaw_client_redacts_secrets():
    text = OpenClawClient.redact("api_key=sk-abcdefghijklmnopqrstuvwxyz")
    assert "sk-" not in text
    assert "<redacted>" in text


def test_openclaw_client_redacts_json_token_fields():
    text = OpenClawClient.redact(
        '{"accessToken":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",'
        '"refresh_token":"refresh-token-value","token":"plain-token-value"}'
    )

    assert "eyJhbGci" not in text
    assert "refresh-token-value" not in text
    assert "plain-token-value" not in text
    assert text.count("<redacted>") == 3


def test_build_scoped_prompt_mentions_skill_and_args():
    prompt = openclaw.build_scoped_prompt(
        tool_name="openclaw_weather",
        skill="weather",
        description="Weather skill",
        original_request="weather in Shanghai",
        args={"request": "today"},
    )

    assert "Skill: weather" in prompt
    assert "Original user request: weather in Shanghai" in prompt
    assert '"request": "today"' in prompt
    assert "Return only the concise result" in prompt


def test_openclaw_tool_schema_uses_generic_request_parameter():
    schemas = _build_runtime_tool_schemas(
        {
            "allowed_tools": ["openclaw_weather"],
            "runtime_spec": {
                "tools": [
                    {
                        "name": "openclaw_weather",
                        "description": "Execute weather through OpenClaw",
                        "provider_type": "openclaw",
                        "provider_ref": "weather",
                        "arg_schema": {
                            "provider": {
                                "openclaw": {"skill": "weather"},
                                "properties": {"request": {"type": "string"}},
                                "required": ["request"],
                            }
                        },
                    }
                ],
                "sub_agents": [],
            },
        },
        "s1",
    )

    assert schemas == [
        {
            "type": "function",
            "function": {
                "name": "openclaw_weather",
                "description": "Execute weather through OpenClaw",
                "parameters": {
                    "type": "object",
                    "properties": {"request": {"type": "string"}},
                    "required": ["request"],
                },
            },
        }
    ]


@pytest.mark.asyncio
async def test_hub_routes_openclaw_provider(monkeypatch):
    async def fake_execute(tool_name, args, *, tool_spec, session_id, original_request):
        assert tool_name == "openclaw_weather"
        assert args == {"request": "weather"}
        assert tool_spec["provider_ref"] == "weather"
        assert session_id == "s1"
        assert original_request == "weather please"
        return "ok"

    monkeypatch.setattr(openclaw, "execute", fake_execute)

    result = await execute_tool_call(
        {
            "session_id": "s1",
            "message": "weather please",
            "runtime_spec": {
                "tools": [
                    {
                        "name": "openclaw_weather",
                        "provider_type": "openclaw",
                        "provider_ref": "weather",
                    }
                ]
            },
        },
        "openclaw_weather",
        {"request": "weather"},
    )

    assert result == "ok"


@pytest.mark.asyncio
async def test_execute_builds_openclaw_agent_command(monkeypatch):
    calls: list[list[str]] = []

    async def fake_exec(*command, stdout=None, stderr=None, env=None):
        calls.append(list(command))
        return FakeProcess(stdout=b'{"response":"Sunny"}')

    monkeypatch.setattr(openclaw, "get_settings", lambda: _settings(openclaw_agent_local=True))
    import src.agent.openclaw_client as client_mod

    monkeypatch.setattr(client_mod.asyncio, "create_subprocess_exec", fake_exec)

    result = await openclaw.execute(
        "openclaw_weather",
        {"request": "weather in Shanghai"},
        tool_spec={
            "description": "Weather",
            "provider_ref": "weather",
            "arg_schema": {"provider": {"openclaw": {"skill": "weather"}}},
        },
        session_id="s1",
        original_request="weather please",
    )

    assert result == "Sunny"
    command = calls[0]
    assert command[:4] == ["openclaw", "agent", "--agent", "coder"]
    assert "--session-id" in command
    assert "--json" in command
    assert "--local" in command
    assert "Skill: weather" in command[command.index("--message") + 1]


@pytest.mark.asyncio
async def test_execute_reports_nonzero_exit(monkeypatch):
    async def fake_exec(*command, stdout=None, stderr=None, env=None):
        return FakeProcess(stderr=b"gateway unavailable", returncode=1)

    monkeypatch.setattr(openclaw, "get_settings", lambda: _settings())
    import src.agent.openclaw_client as client_mod

    monkeypatch.setattr(client_mod.asyncio, "create_subprocess_exec", fake_exec)

    result = await openclaw.execute("openclaw_weather", {"request": "weather"})

    assert "Error executing OpenClaw tool openclaw_weather" in result
    assert "gateway unavailable" in result


@pytest.mark.asyncio
async def test_execute_reports_timeout(monkeypatch):
    proc = FakeProcess()

    async def fake_exec(*command, stdout=None, stderr=None, env=None):
        return proc

    async def fake_wait_for(awaitable, timeout):
        awaitable.close()
        raise TimeoutError

    monkeypatch.setattr(openclaw, "get_settings", lambda: _settings(openclaw_timeout_seconds=1))
    import src.agent.openclaw_client as client_mod

    monkeypatch.setattr(client_mod.asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr(client_mod.asyncio, "wait_for", fake_wait_for)

    result = await openclaw.execute("openclaw_weather", {"request": "weather"})

    assert "timed out after 1 seconds" in result
    assert proc.killed is True
