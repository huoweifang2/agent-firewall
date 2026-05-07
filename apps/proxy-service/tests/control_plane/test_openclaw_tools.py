from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.wizard.services.openclaw import redact_openclaw_payload


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _create_agent(client: AsyncClient) -> dict:
    resp = await client.post(
        "/v1/agents",
        json={
            "name": f"OpenClawAgent-{uuid.uuid4().hex[:8]}",
            "description": "Agent for OpenClaw tool tests",
            "team": "platform",
            "framework": "openclaw",
            "environment": "dev",
            "is_public_facing": False,
            "has_tools": True,
            "has_write_actions": True,
            "touches_pii": False,
            "handles_secrets": False,
            "calls_external_apis": True,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_list_openclaw_skills_redacts_paths(client, monkeypatch):
    async def fake_list_openclaw_skills(*, eligible_only: bool = True):
        assert eligible_only is True
        return [
            {
                "name": "weather",
                "description": "Weather",
                "source": "openclaw-bundled",
                "bundled": True,
                "eligible": True,
                "disabled": False,
                "blocked_by_allowlist": False,
                "emoji": None,
                "homepage": None,
                "missing": {},
                "filePath": "/secret/path",
            }
        ]

    monkeypatch.setattr("src.wizard.routers.openclaw.list_openclaw_skills", fake_list_openclaw_skills)

    resp = await client.get("/v1/openclaw/skills")

    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["name"] == "weather"
    assert "filePath" not in item


@pytest.mark.asyncio
async def test_list_openclaw_agents_redacts_details(client, monkeypatch):
    async def fake_list_openclaw_agents():
        return [
            {
                "id": "coder",
                "name": "Coder",
                "workspace": "/Users/me/.openclaw/workspace",
                "model": "deepseek/deepseek-chat",
                "bindings": 0,
                "is_default": True,
                "agentDir": "/secret/path",
            }
        ]

    monkeypatch.setattr("src.wizard.routers.openclaw.list_openclaw_agents", fake_list_openclaw_agents)

    resp = await client.get("/v1/openclaw/agents")

    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["id"] == "coder"
    assert "agentDir" not in item


@pytest.mark.asyncio
async def test_list_openclaw_hooks(client, monkeypatch):
    async def fake_list_openclaw_hooks():
        return [
            {
                "name": "command-logger",
                "description": "Audit commands",
                "eligible": True,
                "events": ["command"],
                "enabled_by_config": True,
            }
        ]

    monkeypatch.setattr("src.wizard.routers.openclaw.list_openclaw_hooks", fake_list_openclaw_hooks)

    resp = await client.get("/v1/openclaw/hooks")

    assert resp.status_code == 200
    assert resp.json()["items"][0]["name"] == "command-logger"
    assert resp.json()["items"][0]["events"] == ["command"]


def test_redact_openclaw_payload_removes_model_status_secrets():
    payload = {
        "defaultModel": "deepseek/deepseek-chat",
        "auth": {
            "providers": [
                {
                    "provider": "deepseek",
                    "profiles": {
                        "count": 1,
                        "apiKey": 1,
                        "labels": ["deepseek:default=sk-secret-value"],
                    },
                }
            ],
            "shellEnvFallback": {"enabled": True, "appliedKeys": ["DEEPSEEK_API_KEY"]},
        },
    }

    redacted = redact_openclaw_payload(payload)

    assert redacted["defaultModel"] == "deepseek/deepseek-chat"
    assert redacted["auth"]["providers"][0]["profiles"]["apiKey"] == 1
    assert redacted["auth"]["providers"][0]["profiles"]["labels"] == []
    assert redacted["auth"]["shellEnvFallback"]["appliedKeys"] == []
    assert "sk-secret-value" not in str(redacted)


@pytest.mark.asyncio
async def test_import_openclaw_tool_and_runtime_spec(client):
    agent = await _create_agent(client)

    resp = await client.post(f"/v1/agents/{agent['id']}/tools/openclaw/import", json={"skills": ["weather"]})

    assert resp.status_code == 201, resp.text
    tool = resp.json()[0]
    assert tool["name"] == "openclaw_weather"
    assert tool["category"] == "openclaw"
    assert tool["arg_schema"]["provider"]["openclaw"]["skill"] == "weather"
    assert tool["arg_schema"]["provider"]["protection"]["pre_gate_enabled"] is True
    assert tool["arg_schema"]["provider"]["protection"]["post_gate_enabled"] is True
    assert tool["arg_schema"]["provider"]["properties"]["request"]["type"] == "string"

    runtime = await client.get(f"/v1/agents/{agent['id']}/runtime-spec")
    assert runtime.status_code == 200, runtime.text
    runtime_tool = runtime.json()["tools"][0]
    assert runtime_tool["provider_type"] == "openclaw"
    assert runtime_tool["provider_ref"] == "weather"
    assert runtime_tool["pre_gate_enabled"] is True
    assert runtime_tool["post_gate_enabled"] is True


@pytest.mark.asyncio
async def test_import_openclaw_tool_rejects_duplicate(client):
    agent = await _create_agent(client)
    first = await client.post(f"/v1/agents/{agent['id']}/tools/openclaw/import", json={"skills": ["weather"]})
    assert first.status_code == 201, first.text

    duplicate = await client.post(f"/v1/agents/{agent['id']}/tools/openclaw/import", json={"skills": ["weather"]})

    assert duplicate.status_code == 409
    assert "openclaw_weather" in duplicate.text
