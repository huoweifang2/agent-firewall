"""Agent hierarchy and team-template routes."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from proxy_service.application.control_plane.risk import apply_risk_classification
from proxy_service.application.control_plane.tools import apply_smart_defaults
from proxy_service.domain.control_plane.models import (
    AccessType,
    Agent,
    AgentCreatedFrom,
    AgentDelegation,
    AgentEnvironment,
    AgentFramework,
    AgentKind,
    AgentRole,
    AgentSkill,
    AgentStatus,
    AgentTool,
    AgentTraceRun,
    RoleToolPermission,
    RolloutMode,
    Sensitivity,
    SkillScope,
)
from proxy_service.infrastructure.persistence.session import get_db
from proxy_service.interfaces.http.schemas.control_plane import (
    AgentRead,
    AgentTeamRead,
    AgentTeamsResponse,
    AgentTeamSubAgent,
    AgentTeamTemplateCreate,
    DelegationRead,
)

logger = structlog.get_logger()
router = APIRouter(tags=["agent-teams"])


def _binding_to_read(binding: AgentDelegation) -> DelegationRead:
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


async def _count_by_agent(
    db: AsyncSession,
    model: type[AgentTool] | type[AgentRole] | type[AgentSkill],
    agent_ids: set[uuid.UUID],
) -> dict[uuid.UUID, int]:
    if not agent_ids:
        return {}
    rows = (
        await db.execute(
            select(model.agent_id, func.count()).where(model.agent_id.in_(agent_ids)).group_by(model.agent_id)
        )
    ).all()
    return {agent_id: int(count) for agent_id, count in rows}


async def _last_trace_by_agent(db: AsyncSession, agent_ids: set[uuid.UUID]) -> dict[uuid.UUID, object | None]:
    if not agent_ids:
        return {}
    rows = (
        await db.execute(
            select(AgentTraceRun.agent_id, func.max(AgentTraceRun.timestamp))
            .where(AgentTraceRun.agent_id.in_(agent_ids))
            .group_by(AgentTraceRun.agent_id)
        )
    ).all()
    return {agent_id: last_trace for agent_id, last_trace in rows}


@router.get("/agent-teams", response_model=AgentTeamsResponse)
async def list_agent_teams(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> AgentTeamsResponse:
    """Return main agents with their direct subagents."""
    result = await db.execute(
        select(Agent)
        .where(Agent.agent_kind == AgentKind.MAIN_AGENT, Agent.status != AgentStatus.ARCHIVED)
        .order_by(Agent.is_reference.desc(), Agent.created_at.desc())
    )
    main_agents = list(result.scalars().all())
    main_ids = {main.id for main in main_agents}
    bindings_by_parent: dict[uuid.UUID, list[AgentDelegation]] = {agent_id: [] for agent_id in main_ids}

    if main_ids:
        bindings_result = await db.execute(
            select(AgentDelegation)
            .where(AgentDelegation.parent_agent_id.in_(main_ids))
            .options(selectinload(AgentDelegation.child_agent))
            .order_by(AgentDelegation.sort_order, AgentDelegation.created_at)
        )
        for binding in bindings_result.scalars().unique().all():
            bindings_by_parent.setdefault(binding.parent_agent_id, []).append(binding)

    all_agent_ids = set(main_ids)
    for bindings in bindings_by_parent.values():
        for binding in bindings:
            child = binding.child_agent
            if child is not None and child.status != AgentStatus.ARCHIVED:
                all_agent_ids.add(child.id)

    tool_counts = await _count_by_agent(db, AgentTool, all_agent_ids)
    role_counts = await _count_by_agent(db, AgentRole, all_agent_ids)
    skill_counts = await _count_by_agent(db, AgentSkill, all_agent_ids)
    last_traces = await _last_trace_by_agent(db, all_agent_ids)

    items: list[AgentTeamRead] = []

    for main in main_agents:
        sub_entries: list[AgentTeamSubAgent] = []
        for binding in bindings_by_parent.get(main.id, []):
            child = binding.child_agent
            if child is None or child.status == AgentStatus.ARCHIVED:
                continue
            sub_entries.append(
                AgentTeamSubAgent(
                    agent=AgentRead.model_validate(child),
                    binding=_binding_to_read(binding),
                    tools_count=tool_counts.get(child.id, 0),
                    roles_count=role_counts.get(child.id, 0),
                    skills_count=skill_counts.get(child.id, 0),
                    last_trace_at=last_traces.get(child.id),
                )
            )

        items.append(
            AgentTeamRead(
                main_agent=AgentRead.model_validate(main),
                sub_agents=sub_entries,
                tools_count=tool_counts.get(main.id, 0),
                roles_count=role_counts.get(main.id, 0),
                skills_count=skill_counts.get(main.id, 0),
                last_trace_at=last_traces.get(main.id),
            )
        )

    return AgentTeamsResponse(items=items, total=len(items))


async def _create_agent(
    db: AsyncSession,
    *,
    name: str,
    description: str,
    kind: AgentKind,
    team: str,
    template_key: str,
    policy_pack: str,
) -> Agent:
    existing = await db.execute(select(Agent).where(Agent.name == name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Agent '{name}' already exists")
    agent = Agent(
        name=name,
        description=description,
        team=team,
        framework=AgentFramework.OPENCLAW,
        environment=AgentEnvironment.DEV,
        is_public_facing=False,
        has_tools=True,
        has_write_actions=kind == AgentKind.SUB_AGENT,
        touches_pii=False,
        handles_secrets=False,
        calls_external_apis=True,
        status=AgentStatus.ACTIVE,
        rollout_mode=RolloutMode.OBSERVE,
        policy_pack=policy_pack,
        agent_kind=kind,
        created_from=AgentCreatedFrom.TEMPLATE,
        template_key=template_key,
    )
    apply_risk_classification(agent)
    db.add(agent)
    await db.flush()
    return agent


async def _add_tool(
    db: AsyncSession, agent: Agent, name: str, description: str, access: AccessType, sensitivity: Sensitivity
) -> AgentTool:
    tool = AgentTool(
        agent_id=agent.id,
        name=name,
        description=description,
        category="template",
        access_type=access,
        sensitivity=sensitivity,
        returns_pii=False,
        returns_secrets=False,
    )
    apply_smart_defaults(tool)
    db.add(tool)
    await db.flush()
    return tool


async def _add_role_with_tools(db: AsyncSession, agent: Agent, role_name: str, tools: list[AgentTool]) -> AgentRole:
    role = AgentRole(agent_id=agent.id, name=role_name, description=f"Default {role_name} role")
    db.add(role)
    await db.flush()
    for tool in tools:
        db.add(
            RoleToolPermission(
                role_id=role.id,
                tool_id=tool.id,
                scopes=["read", "write"] if tool.access_type == AccessType.WRITE else ["read"],
            )
        )
    return role


async def _add_skill(db: AsyncSession, agent: Agent, name: str, scope: SkillScope, fragment: str) -> None:
    db.add(
        AgentSkill(
            agent_id=agent.id,
            name=name,
            description=fragment,
            scope=scope,
            prompt_fragment=fragment,
        )
    )


@router.post("/agent-team-templates", response_model=AgentTeamRead, status_code=201)
async def create_agent_team_template(
    body: AgentTeamTemplateCreate,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> AgentTeamRead:
    """Create the default Coordinator Team template."""
    if body.template_key != "coordinator_team":
        raise HTTPException(status_code=422, detail="Unknown template_key")

    main = await _create_agent(
        db,
        name="Coordinator Agent",
        description="Understands goals, decomposes tasks, delegates to subagents, and summarizes results.",
        kind=AgentKind.MAIN_AGENT,
        team="agent-team",
        template_key=body.template_key,
        policy_pack="internal_copilot",
    )
    web = await _add_tool(
        db, main, "WEB_SEARCH", "Read-only web search for lightweight coordination.", AccessType.READ, Sensitivity.LOW
    )
    await _add_role_with_tools(db, main, "operator", [web])
    await _add_skill(
        db,
        main,
        "coordinator_planning",
        SkillScope.MAIN_AGENT,
        "Break user goals into concrete sub-tasks, delegate when useful, and merge subagent results.",
    )

    child_defs = [
        (
            "Research Agent",
            "Researches information, gathers sources, and summarizes evidence.",
            [("WEB_SEARCH", "Search the web for research and source gathering.", AccessType.READ, Sensitivity.LOW)],
            "Use for information retrieval, source gathering, and synthesis.",
        ),
        (
            "Action Agent",
            "Executes write-oriented operational actions after confirmation.",
            [
                ("GITHUB", "Work with GitHub repositories and issues.", AccessType.WRITE, Sensitivity.HIGH),
                ("SLACK", "Read and send Slack messages.", AccessType.WRITE, Sensitivity.HIGH),
                ("GMAIL", "Read and send Gmail messages.", AccessType.WRITE, Sensitivity.HIGH),
                ("CALENDAR", "Read and manage calendar events.", AccessType.WRITE, Sensitivity.MEDIUM),
            ],
            "Use for write actions, workflow execution, or external system updates.",
        ),
        (
            "Security Auditor",
            "Reviews outputs, permissions, and possible sensitive-data exposure.",
            [],
            "Use before finalizing risky answers or when a task involves permissions, PII, or secrets.",
        ),
    ]

    sub_entries: list[AgentTeamSubAgent] = []
    for idx, (name, desc, tool_defs, when) in enumerate(child_defs):
        child = await _create_agent(
            db,
            name=name,
            description=desc,
            kind=AgentKind.SUB_AGENT,
            team="agent-team",
            template_key=body.template_key,
            policy_pack="internal_copilot",
        )
        tools = [await _add_tool(db, child, *tool_def) for tool_def in tool_defs]
        await _add_role_with_tools(db, child, "operator", tools)
        await _add_skill(
            db,
            child,
            "focused_execution",
            SkillScope.SUB_AGENT,
            "Complete delegated tasks and return concise structured results.",
        )
        binding = AgentDelegation(
            parent_agent_id=main.id,
            child_agent_id=child.id,
            delegation_description=desc,
            when_to_delegate=when,
            sort_order=idx,
            is_active=True,
        )
        db.add(binding)
        await db.flush()
        sub_entries.append(
            AgentTeamSubAgent(
                agent=AgentRead.model_validate(child),
                binding=_binding_to_read(binding),
                tools_count=len(tools),
                roles_count=1,
                skills_count=1,
            )
        )

    await db.commit()
    logger.info("agent_team_template_created", template_key=body.template_key, main_agent_id=str(main.id))
    return AgentTeamRead(
        main_agent=AgentRead.model_validate(main),
        sub_agents=sub_entries,
        tools_count=1,
        roles_count=1,
        skills_count=1,
    )
