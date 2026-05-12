"""OpenClaw skill discovery router."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Query

from proxy_service.application.control_plane.openclaw import (
    get_openclaw_models_status,
    get_openclaw_status,
    list_openclaw_agents,
    list_openclaw_hooks,
    list_openclaw_skills,
)
from proxy_service.interfaces.http.schemas.control_plane import (
    OpenClawAgentsResponse,
    OpenClawHooksResponse,
    OpenClawSkillsResponse,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/openclaw", tags=["openclaw"])


@router.get("/status")
async def get_status() -> dict:
    """Return local OpenClaw runtime and model status."""
    try:
        status = await get_openclaw_status()
        models = await get_openclaw_models_status()
    except RuntimeError as exc:
        logger.warning("openclaw_status_failed", error=str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"status": status, "models": models}


@router.get("/agents", response_model=OpenClawAgentsResponse)
async def get_openclaw_agents() -> OpenClawAgentsResponse:
    """List redacted local OpenClaw agents."""
    try:
        agents = await list_openclaw_agents()
    except RuntimeError as exc:
        logger.warning("openclaw_agents_list_failed", error=str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return OpenClawAgentsResponse(items=agents)


@router.get("/skills", response_model=OpenClawSkillsResponse)
async def get_openclaw_skills(
    eligible_only: bool = Query(default=True),
) -> OpenClawSkillsResponse:
    """List redacted OpenClaw skills that can be imported as tools."""
    try:
        skills = await list_openclaw_skills(eligible_only=eligible_only)
    except RuntimeError as exc:
        logger.warning("openclaw_skills_list_failed", error=str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return OpenClawSkillsResponse(items=skills)


@router.get("/hooks", response_model=OpenClawHooksResponse)
async def get_openclaw_hooks() -> OpenClawHooksResponse:
    """List redacted local OpenClaw hooks for audit/discovery."""
    try:
        hooks = await list_openclaw_hooks()
    except RuntimeError as exc:
        logger.warning("openclaw_hooks_list_failed", error=str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return OpenClawHooksResponse(items=hooks)
