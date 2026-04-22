"""Runtime-spec and runtime resource router."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.wizard.models import Agent, AgentDelegation, AgentSkill
from src.wizard.schemas import (
    AgentRuntimeSpec,
    DelegationCreate,
    DelegationRead,
    DelegationUpdate,
    SkillCreate,
    SkillRead,
    SkillUpdate,
)
from src.wizard.services.runtime_spec import build_agent_runtime_spec

logger = structlog.get_logger()
router = APIRouter(prefix="/agents/{agent_id}", tags=["runtime"])


async def _get_agent_or_404(agent_id: uuid.UUID, db: AsyncSession) -> Agent:
    agent = await db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/runtime-spec", response_model=AgentRuntimeSpec)
async def get_runtime_spec(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> AgentRuntimeSpec:
    """Return the runtime spec consumed by agent-runtime."""
    try:
        return await build_agent_runtime_spec(agent_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.get("/skills", response_model=list[SkillRead])
async def list_skills(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[SkillRead]:
    await _get_agent_or_404(agent_id, db)
    result = await db.execute(select(AgentSkill).where(AgentSkill.agent_id == agent_id).order_by(AgentSkill.sort_order))
    return list(result.scalars().all())


@router.post("/skills", response_model=SkillRead, status_code=201)
async def create_skill(
    agent_id: uuid.UUID,
    body: SkillCreate,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> SkillRead:
    await _get_agent_or_404(agent_id, db)
    existing = await db.execute(select(AgentSkill).where(AgentSkill.agent_id == agent_id, AgentSkill.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Skill '{body.name}' already exists on this agent")

    skill = AgentSkill(agent_id=agent_id, **body.model_dump())
    db.add(skill)
    await db.commit()
    await db.refresh(skill)
    logger.info("skill_created", agent_id=str(agent_id), skill_id=str(skill.id), name=skill.name)
    return skill


@router.patch("/skills/{skill_id}", response_model=SkillRead)
async def update_skill(
    agent_id: uuid.UUID,
    skill_id: uuid.UUID,
    body: SkillUpdate,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> SkillRead:
    await _get_agent_or_404(agent_id, db)
    skill = await db.get(AgentSkill, skill_id)
    if skill is None or skill.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Skill not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(skill, field, value)

    await db.commit()
    await db.refresh(skill)
    logger.info("skill_updated", agent_id=str(agent_id), skill_id=str(skill.id))
    return skill


@router.delete("/skills/{skill_id}", status_code=204)
async def delete_skill(
    agent_id: uuid.UUID,
    skill_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> None:
    await _get_agent_or_404(agent_id, db)
    skill = await db.get(AgentSkill, skill_id)
    if skill is None or skill.agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Skill not found")
    await db.delete(skill)
    await db.commit()


def _delegation_to_read(binding: AgentDelegation) -> DelegationRead:
    child = binding.child_agent
    return DelegationRead(
        id=binding.id,
        parent_agent_id=binding.parent_agent_id,
        child_agent_id=binding.child_agent_id,
        child_agent_name=child.name if child else None,
        child_agent_description=child.description if child else None,
        delegation_description=binding.delegation_description,
        when_to_delegate=binding.when_to_delegate,
        sort_order=binding.sort_order,
        is_active=binding.is_active,
        created_at=binding.created_at,
        updated_at=binding.updated_at,
    )


@router.get("/sub-agents", response_model=list[DelegationRead])
async def list_sub_agents(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[DelegationRead]:
    await _get_agent_or_404(agent_id, db)
    result = await db.execute(
        select(AgentDelegation)
        .where(AgentDelegation.parent_agent_id == agent_id)
        .order_by(AgentDelegation.sort_order, AgentDelegation.created_at)
    )
    bindings = list(result.scalars().unique().all())
    for binding in bindings:
        await db.refresh(binding, attribute_names=["child_agent"])
    return [_delegation_to_read(binding) for binding in bindings]


@router.post("/sub-agents", response_model=DelegationRead, status_code=201)
async def create_sub_agent(
    agent_id: uuid.UUID,
    body: DelegationCreate,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> DelegationRead:
    await _get_agent_or_404(agent_id, db)
    child = await db.get(Agent, body.child_agent_id)
    if child is None:
        raise HTTPException(status_code=404, detail="Child agent not found")
    if body.child_agent_id == agent_id:
        raise HTTPException(status_code=422, detail="Agent cannot delegate to itself")

    existing = await db.execute(
        select(AgentDelegation).where(
            AgentDelegation.parent_agent_id == agent_id,
            AgentDelegation.child_agent_id == body.child_agent_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Delegation already exists")

    binding = AgentDelegation(parent_agent_id=agent_id, **body.model_dump())
    db.add(binding)
    await db.commit()
    await db.refresh(binding, attribute_names=["child_agent"])
    logger.info("sub_agent_created", agent_id=str(agent_id), child_agent_id=str(body.child_agent_id))
    return _delegation_to_read(binding)


@router.patch("/sub-agents/{binding_id}", response_model=DelegationRead)
async def update_sub_agent(
    agent_id: uuid.UUID,
    binding_id: uuid.UUID,
    body: DelegationUpdate,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> DelegationRead:
    await _get_agent_or_404(agent_id, db)
    binding = await db.get(AgentDelegation, binding_id)
    if binding is None or binding.parent_agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Delegation not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(binding, field, value)

    await db.commit()
    await db.refresh(binding, attribute_names=["child_agent"])
    return _delegation_to_read(binding)


@router.delete("/sub-agents/{binding_id}", status_code=204)
async def delete_sub_agent(
    agent_id: uuid.UUID,
    binding_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> None:
    await _get_agent_or_404(agent_id, db)
    binding = await db.get(AgentDelegation, binding_id)
    if binding is None or binding.parent_agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Delegation not found")
    await db.delete(binding)
    await db.commit()
