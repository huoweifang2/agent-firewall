"""Tests for main/subagent hierarchy."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from src.control_plane.schema_compat import ensure_agent_hierarchy_columns
from src.control_plane.services.runtime_spec import build_agent_runtime_spec
from src.db.session import async_session, engine
from src.main import app


@pytest.fixture
async def client():
    await ensure_agent_hierarchy_columns(engine)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _create_main(client: AsyncClient) -> dict:
    resp = await client.post(
        "/v1/agents",
        json={
            "name": f"Main-{uuid.uuid4().hex[:8]}",
            "description": "main hierarchy test",
            "team": "tests",
            "framework": "openclaw",
            "environment": "dev",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_agent_defaults_to_main_agent(client: AsyncClient):
    agent = await _create_main(client)
    assert agent["agent_kind"] == "main_agent"
    assert agent["created_from"] == "manual"


@pytest.mark.asyncio
async def test_create_subagent_appears_in_agent_teams(client: AsyncClient):
    main = await _create_main(client)
    resp = await client.post(
        f"/v1/agents/{main['id']}/sub-agents/create",
        json={
            "name": f"Sub-{uuid.uuid4().hex[:8]}",
            "description": "research helper",
            "when_to_delegate": "Delegate research tasks.",
        },
    )
    assert resp.status_code == 201, resp.text
    binding = resp.json()
    assert binding["parent_agent_id"] == main["id"]
    assert binding["child_agent_name"].startswith("Sub-")

    teams_resp = await client.get("/v1/agent-teams")
    assert teams_resp.status_code == 200
    teams = teams_resp.json()["items"]
    team = next(item for item in teams if item["main_agent"]["id"] == main["id"])
    assert len(team["sub_agents"]) == 1
    assert team["sub_agents"][0]["agent"]["agent_kind"] == "sub_agent"


@pytest.mark.asyncio
async def test_runtime_spec_exposes_create_and_delegate_tools(client: AsyncClient):
    main = await _create_main(client)
    sub_resp = await client.post(
        f"/v1/agents/{main['id']}/sub-agents/create",
        json={
            "name": f"RuntimeSub-{uuid.uuid4().hex[:8]}",
            "description": "runtime helper",
            "when_to_delegate": "Delegate runtime tasks.",
        },
    )
    assert sub_resp.status_code == 201
    child_id = sub_resp.json()["child_agent_id"]

    async with async_session() as session:
        main_spec = await build_agent_runtime_spec(uuid.UUID(main["id"]), session)
        assert main_spec.agent_kind.value == "main_agent"
        assert any(sa.name.startswith("RuntimeSub-") for sa in main_spec.sub_agents)

        child_spec = await build_agent_runtime_spec(uuid.UUID(child_id), session)
        assert child_spec.agent_kind.value == "sub_agent"
        assert child_spec.sub_agents == []
