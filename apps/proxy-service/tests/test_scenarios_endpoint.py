"""Tests for public attack-scenario catalogue endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from proxy_service.bootstrap.main import app


@pytest.fixture
async def client():
    """Async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["playground", "agent", "compare"])
async def test_scenarios_catalogue_loads(kind: str, client: AsyncClient) -> None:
    response = await client.get(f"/v1/scenarios/{kind}")

    assert response.status_code == 200
    groups = response.json()
    assert groups
    assert groups[0]["items"]
    assert groups[0]["items"][0]["prompt"]
