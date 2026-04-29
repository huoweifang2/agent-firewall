"""OpenClaw skill discovery router."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Query

from src.wizard.schemas import OpenClawSkillsResponse
from src.wizard.services.openclaw import list_openclaw_skills

logger = structlog.get_logger()

router = APIRouter(prefix="/openclaw", tags=["openclaw"])


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
