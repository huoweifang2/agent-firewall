"""Async database session factory and optional cache client."""

from collections.abc import AsyncGenerator
from time import monotonic
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from proxy_service.infrastructure.config import get_settings

settings = get_settings()


class MemoryCache:
    """Small async Redis-like cache used when Redis is not configured."""

    def __init__(self) -> None:
        self._items: dict[str, tuple[str, float | None]] = {}

    async def get(self, key: str) -> str | None:
        item = self._items.get(key)
        if item is None:
            return None
        value, expires_at = item
        if expires_at is not None and expires_at <= monotonic():
            self._items.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: str, ex: int | None = None, **_: Any) -> bool:
        expires_at = monotonic() + ex if ex else None
        self._items[key] = (value, expires_at)
        return True

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self._items:
                deleted += 1
                self._items.pop(key, None)
        return deleted

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        self._items.clear()


CacheClient = Redis | MemoryCache


def _is_sqlite_url(database_url: str) -> bool:
    return database_url.startswith("sqlite")


def _ensure_sqlite_parent(database_url: str) -> None:
    if not _is_sqlite_url(database_url):
        return
    database = make_url(database_url).database
    if not database or database == ":memory:":
        return
    from pathlib import Path

    Path(database).expanduser().parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent(settings.database_url)

_engine_kwargs = {"echo": False, "pool_pre_ping": True}
if not _is_sqlite_url(settings.database_url):
    _engine_kwargs.update({"pool_size": 5, "max_overflow": 10})

engine = create_async_engine(settings.database_url, **_engine_kwargs)

if _is_sqlite_url(settings.database_url):

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session (FastAPI dependency)."""
    async with async_session() as session:
        yield session


_cache_client: CacheClient | None = None


def cache_mode() -> str:
    """Return the active cache mode label."""
    if settings.cache_backend.lower() == "redis" and settings.redis_url.strip():
        return "redis"
    return "memory"


async def get_redis() -> CacheClient:
    """Return a shared Redis-compatible cache client."""
    global _cache_client  # noqa: PLW0603
    if _cache_client is None:
        if cache_mode() == "redis":
            _cache_client = Redis.from_url(settings.redis_url, decode_responses=True)
        else:
            _cache_client = MemoryCache()
    return _cache_client


async def close_db() -> None:
    """Dispose the SQLAlchemy engine."""
    await engine.dispose()


async def close_redis() -> None:
    """Close the cache connection."""
    global _cache_client  # noqa: PLW0603
    if _cache_client is not None:
        await _cache_client.aclose()
        _cache_client = None
