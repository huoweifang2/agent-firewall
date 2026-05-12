"""Proxy service startup and shutdown orchestration."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from proxy_service.infrastructure.config import get_settings
from proxy_service.infrastructure.persistence.models import Base
from proxy_service.infrastructure.persistence.schema_compat import ensure_agent_hierarchy_columns
from proxy_service.infrastructure.persistence.seed import seed_denylist, seed_policies
from proxy_service.infrastructure.persistence.session import async_session, close_db, close_redis, engine
from proxy_service.infrastructure.telemetry.logger import setup_logging
from proxy_service.interfaces.http.routers.control_plane import seed_control_plane

logger = structlog.get_logger()


async def _ensure_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_agent_hierarchy_columns(engine)


async def _seed_startup_data() -> None:
    await seed_policies()
    await seed_denylist()
    await seed_control_plane()


async def _cancel_stale_benchmark_runs() -> None:
    from proxy_service.infrastructure.persistence.red_team.repository import BenchmarkRunRepository

    async with async_session() as session:
        repo = BenchmarkRunRepository(session)
        cancelled = await repo.cancel_stale_runs()
        await session.commit()
        if cancelled:
            logger.info("stale_runs_cancelled", count=cancelled)


async def _cleanup_expired_auth_secrets() -> int:
    from proxy_service.application.red_team.service import cleanup_expired_secrets

    async with async_session() as session:
        return await cleanup_expired_secrets(session)


async def _preload_scanners() -> None:
    """Warm up heavy ML singletons so the first request is fast."""
    settings = get_settings()
    try:
        if settings.enable_llm_guard:
            from proxy_service.domain.firewall.pipeline.nodes.llm_guard import get_scanners

            logger.info("preload_start", scanner="llm_guard")
            await asyncio.to_thread(get_scanners, {})
        if settings.enable_nemo_guardrails:
            from proxy_service.domain.firewall.pipeline.nodes.nemo_guardrails import get_rails

            logger.info("preload_start", scanner="nemo_guardrails")
            await asyncio.to_thread(get_rails)
        if settings.enable_presidio:
            from proxy_service.domain.firewall.pipeline.nodes.presidio import get_analyzer, get_anonymizer

            logger.info("preload_start", scanner="presidio")
            await asyncio.to_thread(get_analyzer)
            await asyncio.to_thread(get_anonymizer)
        logger.info("preload_complete", msg="All ML models loaded")
    except Exception as exc:
        logger.error(
            "preload_failed",
            error_type=type(exc).__name__,
            msg="Non-fatal - models will lazy-load on first request",
        )


async def _periodic_secret_cleanup() -> None:
    while True:
        await asyncio.sleep(3600)
        try:
            cleaned = await _cleanup_expired_auth_secrets()
            if cleaned:
                logger.info("periodic_secrets_cleaned", count=cleaned)
        except Exception:
            logger.warning("periodic_secret_cleanup_failed", exc_info=True)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan hook for the proxy composition root."""
    settings = get_settings()
    setup_logging(log_level=settings.log_level, json_logs=settings.json_logs)
    os.environ["LITELLM_LOG"] = settings.litellm_log_level

    logger.info("proxy_starting", version=settings.app_version)
    await _ensure_schema()
    await _seed_startup_data()
    await _cancel_stale_benchmark_runs()

    cleaned = await _cleanup_expired_auth_secrets()
    if cleaned:
        logger.info("expired_secrets_cleaned", count=cleaned)

    asyncio.create_task(_preload_scanners())
    cleanup_task = asyncio.create_task(_periodic_secret_cleanup())

    logger.info("proxy_ready")
    try:
        yield
    finally:
        cleanup_task.cancel()
        await close_db()
        await close_redis()
        logger.info("proxy_stopped")
