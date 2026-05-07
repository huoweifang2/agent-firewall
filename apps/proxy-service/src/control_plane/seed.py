"""Seed the Telegram-first OpenClaw gateway agent."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.control_plane.models import (
    AccessType,
    Agent,
    AgentCreatedFrom,
    AgentEnvironment,
    AgentFramework,
    AgentKind,
    AgentRole,
    AgentSkill,
    AgentStatus,
    AgentTool,
    RoleToolPermission,
    RolloutMode,
    Sensitivity,
    SkillScope,
)
from src.control_plane.services.openclaw import list_openclaw_skills, openclaw_arg_schema, openclaw_tool_name
from src.control_plane.services.risk import apply_risk_classification
from src.control_plane.services.tools import apply_smart_defaults
from src.db.session import async_session

logger = structlog.get_logger()

GATEWAY_AGENT = {
    "name": "Telegram OpenClaw Gateway",
    "description": (
        "Telegram-first OpenClaw agent protected by Agent-Firewall input scanning, "
        "pre-tool gates, post-tool gates, approval queue, and trace logging."
    ),
    "team": "personal",
    "framework": AgentFramework.OPENCLAW,
    "environment": AgentEnvironment.PRODUCTION,
    "is_public_facing": True,
    "has_tools": True,
    "has_write_actions": True,
    "touches_pii": True,
    "handles_secrets": True,
    "calls_external_apis": True,
    "status": AgentStatus.ACTIVE,
    "is_reference": True,
    "rollout_mode": RolloutMode.ENFORCE,
    "policy_pack": "telegram_gateway",
    "agent_kind": AgentKind.MAIN_AGENT,
    "created_from": AgentCreatedFrom.TEMPLATE,
    "template_key": "telegram_openclaw_gateway",
    "generated_config": {
        "openclaw_agent_id": "coder",
        "generated_at": datetime.now(UTC).isoformat(),
    },
}

DEFAULT_ROLES = [
    {"name": "customer", "description": "Default Telegram user role.", "inherits_from": None},
    {"name": "operator", "description": "Local owner/operator role.", "inherits_from": "customer"},
]

DEFAULT_SKILLS = [
    {
        "name": "telegram_first_boundary",
        "description": "Keep Telegram as the entry point and route capabilities through Agent-Firewall gates.",
        "scope": SkillScope.SHARED,
        "prompt_fragment": (
            "Treat Telegram as the user entry point. Use only Agent-Firewall registered tools, "
            "skills, MCP providers, and subagents."
        ),
        "constraints": ["Do not bypass Agent-Firewall tool gates."],
        "output_contract": "Return concise user-visible answers suitable for Telegram.",
        "sort_order": 0,
    }
]

LEGACY_AGENT_NAMES = {"E-commerce Assistant", "Python Shop Agent"}


async def _archive_legacy_agents(session: AsyncSession) -> None:
    result = await session.execute(select(Agent).where(Agent.name.in_(LEGACY_AGENT_NAMES)))
    for agent in result.scalars().all():
        agent.status = AgentStatus.ARCHIVED
        agent.is_reference = False
        logger.info("legacy_seed_agent_archived", agent=agent.name)


async def _gateway_agent(session: AsyncSession) -> Agent:
    result = await session.execute(select(Agent).where(Agent.name == GATEWAY_AGENT["name"]))
    agent = result.scalar_one_or_none()
    if agent is None:
        agent = Agent(**GATEWAY_AGENT)
        apply_risk_classification(agent)
        session.add(agent)
        await session.flush()
        logger.info("gateway_seed_agent_created", agent=agent.name)
    else:
        for key, value in GATEWAY_AGENT.items():
            if key == "name":
                continue
            setattr(agent, key, value)
        apply_risk_classification(agent)
    return agent


async def _ensure_roles(session: AsyncSession, agent: Agent) -> dict[str, AgentRole]:
    result = await session.execute(select(AgentRole).where(AgentRole.agent_id == agent.id))
    roles = {role.name: role for role in result.scalars().all()}
    for spec in DEFAULT_ROLES:
        if spec["name"] in roles:
            continue
        parent = roles.get(str(spec["inherits_from"])) if spec["inherits_from"] else None
        role = AgentRole(
            agent_id=agent.id,
            name=spec["name"],
            description=spec["description"],
            inherits_from=parent.id if parent else None,
        )
        session.add(role)
        await session.flush()
        roles[role.name] = role
    return roles


async def _eligible_openclaw_skill_names() -> list[str]:
    try:
        skills = await list_openclaw_skills(eligible_only=True)
    except Exception as exc:
        logger.warning("gateway_seed_openclaw_skills_unavailable", error=str(exc)[:300])
        return []
    names = [str(skill.get("name", "")).strip() for skill in skills if str(skill.get("name", "")).strip()]
    return sorted(dict.fromkeys(names))


async def _ensure_tools(session: AsyncSession, agent: Agent) -> dict[str, AgentTool]:
    result = await session.execute(select(AgentTool).where(AgentTool.agent_id == agent.id))
    tools = {tool.name: tool for tool in result.scalars().all()}
    skill_names = await _eligible_openclaw_skill_names()
    if not skill_names:
        skill_names = ["summarize"]

    for skill in skill_names:
        name = openclaw_tool_name(skill)
        if name in tools:
            continue
        tool = AgentTool(
            agent_id=agent.id,
            name=name,
            description=f"Execute the OpenClaw '{skill}' skill through Agent-Firewall gates.",
            category="openclaw",
            access_type=AccessType.WRITE,
            sensitivity=Sensitivity.MEDIUM,
            arg_schema=openclaw_arg_schema(skill),
            returns_pii=False,
            returns_secrets=False,
        )
        apply_smart_defaults(tool)
        session.add(tool)
        await session.flush()
        tools[tool.name] = tool
    return tools


async def _ensure_permissions(
    session: AsyncSession,
    roles: dict[str, AgentRole],
    tools: dict[str, AgentTool],
) -> None:
    role_ids = [role.id for role in roles.values()]
    existing_result = await session.execute(select(RoleToolPermission).where(RoleToolPermission.role_id.in_(role_ids)))
    existing = {(perm.role_id, perm.tool_id) for perm in existing_result.scalars().all()}
    for role in roles.values():
        for tool in tools.values():
            key = (role.id, tool.id)
            if key in existing:
                continue
            session.add(
                RoleToolPermission(
                    role_id=role.id,
                    tool_id=tool.id,
                    scopes=["read", "write"] if tool.access_type == AccessType.WRITE else ["read"],
                )
            )


async def _ensure_skills(session: AsyncSession, agent: Agent) -> None:
    result = await session.execute(select(AgentSkill).where(AgentSkill.agent_id == agent.id))
    existing = {skill.name for skill in result.scalars().all()}
    for spec in DEFAULT_SKILLS:
        if spec["name"] not in existing:
            session.add(AgentSkill(agent_id=agent.id, **spec))


async def seed_control_plane() -> None:
    """Seed the single Telegram/OpenClaw gateway agent."""
    async with async_session() as session:
        await _archive_legacy_agents(session)
        agent = await _gateway_agent(session)
        roles = await _ensure_roles(session, agent)
        tools = await _ensure_tools(session, agent)
        await _ensure_permissions(session, roles, tools)
        await _ensure_skills(session, agent)
        await session.commit()
        logger.info("gateway_seed_complete", agent=agent.name, tools=len(tools), roles=len(roles))


REFERENCE_AGENT = GATEWAY_AGENT


async def seed_reference_agent() -> None:
    """Backward-compatible alias used by tests."""
    await seed_control_plane()


async def seed_reference_tools_and_roles() -> None:
    """Backward-compatible alias used by tests."""
    await seed_control_plane()
