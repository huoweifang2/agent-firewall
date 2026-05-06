"""Shared fixtures for proxy-service tests."""

from __future__ import annotations

# ruff: noqa: E402,I001

import os
import tempfile
from pathlib import Path

import pytest

_TEST_DB_PATH = Path(tempfile.gettempdir()) / "agent-firewall-proxy-test.sqlite"
_TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
for suffix in ("", "-wal", "-shm"):
    Path(f"{_TEST_DB_PATH}{suffix}").unlink(missing_ok=True)

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB_PATH}"
os.environ["CACHE_BACKEND"] = "memory"
os.environ["REDIS_URL"] = ""
os.environ["ENABLE_LANGFUSE"] = "false"

from src.db.seed import seed_denylist, seed_policies
from src.db.session import engine
from src.models import Base  # noqa: F401 — triggers model registration
from src.wizard.schema_compat import ensure_agent_hierarchy_columns

_db_seeded = False


@pytest.fixture(autouse=True)
async def _setup_db():
    """Manage DB lifecycle for each test.

    * **Engine dispose** runs before every test — each pytest-asyncio
      test function gets its own event loop, but the engine is a
      module-level singleton.  Disposing prevents ``RuntimeError:
      Future attached to a different loop``.
    * **Table creation + seeding** runs only once (first test).
      ``create_all`` is DDL-idempotent and the seed helpers use
      INSERT-IF-NOT-EXISTS, so running them once per session is safe.
      Tests that mutate policies use unique names and clean up after
      themselves.
    """
    global _db_seeded  # noqa: PLW0603

    await engine.dispose()

    if not _db_seeded:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await ensure_agent_hierarchy_columns(engine)
        await seed_policies()
        await seed_denylist()
        _db_seeded = True

    yield
    await engine.dispose()
