"""Operator intervention queue API."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.models.intervention import Intervention
from src.schemas.intervention import (
    InterventionCreate,
    InterventionListResponse,
    InterventionRead,
    InterventionUpdate,
)

logger = structlog.get_logger()
router = APIRouter(tags=["interventions"])


@router.post("/interventions", response_model=InterventionRead, status_code=201)
async def create_intervention(
    body: InterventionCreate,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Intervention:
    row = Intervention(**body.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    logger.info("intervention_created", intervention_id=str(row.id), kind=row.kind, source=row.source)
    return row


@router.get("/interventions", response_model=InterventionListResponse)
async def list_interventions(
    status: str | None = Query(default=None),
    source: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> InterventionListResponse:
    stmt = select(Intervention)
    count_stmt = select(func.count()).select_from(Intervention)
    if status:
        stmt = stmt.where(Intervention.status == status)
        count_stmt = count_stmt.where(Intervention.status == status)
    if source:
        stmt = stmt.where(Intervention.source == source)
        count_stmt = count_stmt.where(Intervention.source == source)
    if session_id:
        stmt = stmt.where(Intervention.session_id == session_id)
        count_stmt = count_stmt.where(Intervention.session_id == session_id)

    total = (await db.execute(count_stmt)).scalar() or 0
    rows = (await db.execute(stmt.order_by(Intervention.created_at.desc()).offset(offset).limit(limit))).scalars().all()
    return InterventionListResponse(
        items=[InterventionRead.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/interventions/{intervention_id}", response_model=InterventionRead)
async def get_intervention(
    intervention_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Intervention:
    row = await db.get(Intervention, intervention_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Intervention not found")
    return row


@router.patch("/interventions/{intervention_id}", response_model=InterventionRead)
async def update_intervention(
    intervention_id: uuid.UUID,
    body: InterventionUpdate,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> Intervention:
    row = await db.get(Intervention, intervention_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Intervention not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(row, key, value)

    await db.commit()
    await db.refresh(row)
    logger.info("intervention_updated", intervention_id=str(row.id), status=row.status)
    return row
