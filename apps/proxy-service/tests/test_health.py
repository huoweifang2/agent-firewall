"""Tests for the health endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client():
    """Async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """GET /health should return 200 with status field."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert "services" in data
    assert "version" in data
    assert set(data["services"].keys()) == {"db", "redis", "langfuse"}
    assert data["services"]["db"]["status"] == "ok"
    assert data["services"]["redis"] == {"status": "skipped", "detail": "memory cache"}
    assert data["services"]["langfuse"]["status"] == "skipped"


@pytest.mark.asyncio
async def test_health_has_correlation_id(client: AsyncClient):
    """Health response should include X-Correlation-ID header."""
    response = await client.get("/health")
    assert "x-correlation-id" in response.headers


@pytest.mark.asyncio
async def test_runtime_config_reports_sqlite_memory_langfuse(client: AsyncClient):
    """Runtime config should expose safe local SQLite defaults."""
    response = await client.get("/v1/runtime/config")
    assert response.status_code == 200
    data = response.json()
    assert data["database_kind"] == "sqlite"
    assert data["sqlite_path"].endswith("agent-firewall-proxy-test.sqlite")
    assert data["cache_mode"] == "memory"
    assert data["redis_configured"] is False
    assert data["langfuse_enabled"] is False
