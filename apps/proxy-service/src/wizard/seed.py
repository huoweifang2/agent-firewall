"""Seed data for the Agent Wizard.

Seeds two fully-configured demo agents so first-time users immediately
see working examples with tools, roles, policies, and generated config.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import async_session
from src.wizard.models import (
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
    RoleToolPermission,
    RolloutMode,
    Sensitivity,
    SkillScope,
)
from src.wizard.services.config_gen import (
    generate_limits_yaml,
    generate_policy_yaml,
    generate_rbac_yaml,
)
from src.wizard.services.integration_kit import generate_integration_kit
from src.wizard.services.risk import apply_risk_classification
from src.wizard.services.tools import apply_smart_defaults

logger = structlog.get_logger()

# ═══════════════════════════════════════════════════════════════════════
# Shared tools (match test agents: shared/tool_definitions.py)
# ═══════════════════════════════════════════════════════════════════════

ECOMMERCE_TOOLS = [
    {
        "name": "getOrders",
        "description": "List all customer orders with status and amounts",
        "category": "orders",
        "access_type": AccessType.READ,
        "sensitivity": Sensitivity.LOW,
        "returns_pii": False,
        "returns_secrets": False,
    },
    {
        "name": "getUsers",
        "description": "List all users. Returns PII (emails, phone numbers). Admin-only",
        "category": "users",
        "access_type": AccessType.READ,
        "sensitivity": Sensitivity.MEDIUM,
        "returns_pii": True,
        "returns_secrets": False,
    },
    {
        "name": "searchProducts",
        "description": "Search products by name or category",
        "category": "products",
        "access_type": AccessType.READ,
        "sensitivity": Sensitivity.LOW,
        "returns_pii": False,
        "returns_secrets": False,
    },
    {
        "name": "updateOrder",
        "description": "Update an order status. Requires admin role",
        "category": "orders",
        "access_type": AccessType.WRITE,
        "sensitivity": Sensitivity.HIGH,
        "returns_pii": False,
        "returns_secrets": False,
    },
    {
        "name": "updateUser",
        "description": "Update a user profile. Requires admin role",
        "category": "users",
        "access_type": AccessType.WRITE,
        "sensitivity": Sensitivity.HIGH,
        "returns_pii": True,
        "returns_secrets": False,
    },
]

ECOMMERCE_ROLES = [
    {"name": "user", "description": "Standard user — read-only access to orders and products", "inherits_from": None},
    {
        "name": "admin",
        "description": "Administrator — full access including PII and write operations",
        "inherits_from": "user",
    },
]

ECOMMERCE_PERMISSIONS: dict[str, list[str]] = {
    "user": ["getOrders", "searchProducts"],
    "admin": ["getUsers", "updateOrder", "updateUser"],
}

# ═══════════════════════════════════════════════════════════════════════
# Agent definitions
# ═══════════════════════════════════════════════════════════════════════

SEED_AGENTS: list[dict] = [
    {
        "agent": {
            "name": "E-commerce Assistant",
            "description": (
                "OpenClaw-backed e-commerce assistant that handles order lookups, "
                "user management, and product search. Uses tool calls for "
                "retrieving orders, users, products, and admin write operations. "
                "Connected through the Agent-Firewall OpenClaw shell."
            ),
            "team": "commerce",
            "framework": AgentFramework.OPENCLAW,
            "environment": AgentEnvironment.PRODUCTION,
            "is_public_facing": True,
            "has_tools": True,
            "has_write_actions": True,
            "touches_pii": True,
            "handles_secrets": False,
            "calls_external_apis": False,
            "status": AgentStatus.ACTIVE,
            "is_reference": True,
            "rollout_mode": RolloutMode.ENFORCE,
            "policy_pack": "customer_support",
            "agent_kind": AgentKind.MAIN_AGENT,
            "created_from": AgentCreatedFrom.TEMPLATE,
            "template_key": "reference_ecommerce",
        },
        "tools": ECOMMERCE_TOOLS,
        "roles": ECOMMERCE_ROLES,
        "permissions": ECOMMERCE_PERMISSIONS,
        "skills": [
            {
                "name": "customer_support_tone",
                "description": "Respond in a concise and helpful customer-support tone.",
                "scope": SkillScope.SHARED,
                "prompt_fragment": "Keep responses concise, operational, and customer-facing. Prefer action over explanation.",
            },
            {
                "name": "handoff_to_python_specialist",
                "description": "Delegate implementation-heavy or data-normalization tasks to the Python specialist.",
                "scope": SkillScope.MAIN_AGENT,
                "prompt_fragment": "When the task requires code-heavy transformation or deterministic data reshaping, prefer delegating to the Python Shop Agent.",
            },
        ],
    },
    {
        "agent": {
            "name": "Python Shop Agent",
            "description": (
                "OpenClaw staging agent that handles order, user, and product operations "
                "behind the same Agent-Firewall gateway."
            ),
            "team": "commerce",
            "framework": AgentFramework.OPENCLAW,
            "environment": AgentEnvironment.STAGING,
            "is_public_facing": False,
            "has_tools": True,
            "has_write_actions": True,
            "touches_pii": True,
            "handles_secrets": False,
            "calls_external_apis": False,
            "status": AgentStatus.ACTIVE,
            "is_reference": True,
            "rollout_mode": RolloutMode.OBSERVE,
            "policy_pack": "internal_copilot",
            "agent_kind": AgentKind.SUB_AGENT,
            "created_from": AgentCreatedFrom.TEMPLATE,
            "template_key": "reference_ecommerce",
        },
        "tools": ECOMMERCE_TOOLS,
        "roles": ECOMMERCE_ROLES,
        "permissions": ECOMMERCE_PERMISSIONS,
        "skills": [
            {
                "name": "python_data_processing",
                "description": "Handle transformation-heavy or deterministic processing tasks.",
                "scope": SkillScope.SUB_AGENT,
                "prompt_fragment": "You are the Python specialist. Focus on deterministic processing, normalization, and precise operational outputs.",
            }
        ],
    },
]


# ═══════════════════════════════════════════════════════════════════════
# Seed helpers
# ═══════════════════════════════════════════════════════════════════════


async def _create_tools(
    session: AsyncSession,
    agent: Agent,
    tools_data: list[dict],
) -> dict[str, AgentTool]:
    """Create tools for an agent, applying smart defaults."""
    tool_map: dict[str, AgentTool] = {}
    for tool_data in tools_data:
        tool = AgentTool(agent_id=agent.id, **tool_data)
        apply_smart_defaults(tool)
        session.add(tool)
        tool_map[tool.name] = tool
    await session.flush()
    return tool_map


async def _create_roles(
    session: AsyncSession,
    agent: Agent,
    roles_data: list[dict],
) -> dict[str, AgentRole]:
    """Create roles with inheritance chain."""
    role_map: dict[str, AgentRole] = {}
    for role_data in roles_data:
        parent_name = role_data["inherits_from"]
        inherits_from = role_map[parent_name].id if parent_name else None
        role = AgentRole(
            agent_id=agent.id,
            name=role_data["name"],
            description=role_data["description"],
            inherits_from=inherits_from,
        )
        session.add(role)
        await session.flush()
        role_map[role.name] = role
    return role_map


async def _assign_permissions(
    session: AsyncSession,
    role_map: dict[str, AgentRole],
    tool_map: dict[str, AgentTool],
    permissions: dict[str, list[str]],
) -> None:
    """Assign tool permissions to roles."""
    for role_name, tool_names in permissions.items():
        role = role_map[role_name]
        for tool_name in tool_names:
            tool = tool_map[tool_name]
            perm = RoleToolPermission(
                role_id=role.id,
                tool_id=tool.id,
                scopes=["read"] if tool.access_type == AccessType.READ else ["read", "write"],
            )
            session.add(perm)


async def _create_skills(
    session: AsyncSession,
    agent: Agent,
    skills_data: list[dict],
) -> None:
    """Create skills for an agent."""
    for skill_data in skills_data:
        session.add(AgentSkill(agent_id=agent.id, **skill_data))
    await session.flush()


async def _ensure_seed_extensions(
    session: AsyncSession,
    seed_agents_by_name: dict[str, Agent],
) -> None:
    """Ensure skills and delegations exist even for already-seeded agents."""
    for seed_def in SEED_AGENTS:
        agent_name = seed_def["agent"]["name"]
        agent = seed_agents_by_name.get(agent_name)
        if agent is None:
            continue
        agent.agent_kind = seed_def["agent"].get("agent_kind", agent.agent_kind)
        agent.created_from = seed_def["agent"].get("created_from", agent.created_from)
        agent.template_key = seed_def["agent"].get("template_key", agent.template_key)

        existing_skills = await session.execute(select(AgentSkill).where(AgentSkill.agent_id == agent.id))
        if existing_skills.scalars().first() is None and seed_def.get("skills"):
            await _create_skills(session, agent, seed_def["skills"])

    parent = seed_agents_by_name.get("E-commerce Assistant")
    child = seed_agents_by_name.get("Python Shop Agent")
    if parent is not None and child is not None:
        existing_binding = await session.execute(
            select(AgentDelegation).where(
                AgentDelegation.parent_agent_id == parent.id,
                AgentDelegation.child_agent_id == child.id,
            )
        )
        if existing_binding.scalar_one_or_none() is None:
            session.add(
                AgentDelegation(
                    parent_agent_id=parent.id,
                    child_agent_id=child.id,
                    delegation_description="Use the Python Shop Agent for implementation-heavy or normalization tasks.",
                    when_to_delegate="Delegate when the request needs structured data processing, normalization, or deterministic execution.",
                )
            )
            await session.flush()


async def _generate_and_cache_config(
    session: AsyncSession,
    agent: Agent,
) -> None:
    """Generate config YAMLs + integration kit and store on agent record."""
    try:
        rbac_yaml = await generate_rbac_yaml(agent.id, session)
        limits_yaml = await generate_limits_yaml(agent.id, session)
        policy_yaml = await generate_policy_yaml(agent.id, session)

        agent.generated_config = {
            "rbac_yaml": rbac_yaml,
            "limits_yaml": limits_yaml,
            "policy_yaml": policy_yaml,
            "generated_at": datetime.now(UTC).isoformat(),
        }

        kit = await generate_integration_kit(agent.id, session)
        agent.generated_kit = kit

        logger.info(
            "seed_config_generated",
            agent=agent.name,
            framework=kit.get("framework"),
        )
    except Exception:
        logger.exception("seed_config_generation_failed", agent=agent.name)


# ═══════════════════════════════════════════════════════════════════════
# Main seed functions
# ═══════════════════════════════════════════════════════════════════════


async def _seed_one_agent(seed_def: dict) -> None:
    """Create one fully-configured agent (idempotent)."""
    agent_data = seed_def["agent"]
    agent_name = agent_data["name"]

    async with async_session() as session:
        # ── Check existence ─────────────────────────────────────────
        result = await session.execute(select(Agent).where(Agent.name == agent_name))
        existing = result.scalar_one_or_none()

        if existing is not None:
            # If agent exists but has no generated config, regenerate it
            await _ensure_seed_extensions(session, {existing.name: existing})
            if existing.generated_config is None:
                logger.info("seed_regenerate_config", agent=agent_name)
                await _generate_and_cache_config(session, existing)
                await session.commit()
            else:
                await session.commit()
                logger.debug("seed_agent_exists", name=agent_name)
            return

        # ── Create agent ────────────────────────────────────────────
        agent = Agent(**agent_data)
        apply_risk_classification(agent)
        session.add(agent)
        await session.flush()

        logger.info(
            "seed_agent_created",
            name=agent.name,
            framework=agent.framework.value,
            risk=str(agent.risk_level),
            protection=str(agent.protection_level),
            policy_pack=agent.policy_pack,
        )

        # ── Create tools ────────────────────────────────────────────
        tool_map = await _create_tools(session, agent, seed_def["tools"])

        # ── Create roles ────────────────────────────────────────────
        role_map = await _create_roles(session, agent, seed_def["roles"])

        # ── Assign permissions ──────────────────────────────────────
        await _assign_permissions(session, role_map, tool_map, seed_def["permissions"])
        await session.flush()

        # ── Create skills ───────────────────────────────────────────
        if seed_def.get("skills"):
            await _create_skills(session, agent, seed_def["skills"])

        # ── Generate config + integration kit ───────────────────────
        await _generate_and_cache_config(session, agent)

        await session.commit()
        logger.info(
            "seed_agent_complete",
            agent=agent.name,
            tools=len(seed_def["tools"]),
            roles=len(seed_def["roles"]),
            has_config=agent.generated_config is not None,
            has_kit=agent.generated_kit is not None,
        )


async def seed_wizard() -> None:
    """Seed all demo agents with full configuration."""
    for seed_def in SEED_AGENTS:
        await _seed_one_agent(seed_def)

    async with async_session() as session:
        agents_result = await session.execute(select(Agent))
        agents = {agent.name: agent for agent in agents_result.scalars().all()}
        await _ensure_seed_extensions(session, agents)
        await session.commit()


# ═══════════════════════════════════════════════════════════════════════
# Backward-compatible aliases (used by tests)
# ═══════════════════════════════════════════════════════════════════════

REFERENCE_AGENT = SEED_AGENTS[0]["agent"]


async def seed_reference_agent() -> None:
    """Legacy alias — seeds the first demo agent only."""
    agent_data = SEED_AGENTS[0]["agent"]
    async with async_session() as session:
        result = await session.execute(select(Agent).where(Agent.name == agent_data["name"]))
        if result.scalar_one_or_none() is not None:
            return
        agent = Agent(**agent_data)
        apply_risk_classification(agent)
        session.add(agent)
        await session.commit()


async def seed_reference_tools_and_roles() -> None:
    """Legacy alias — seeds tools/roles for the first demo agent."""
    agent_data = SEED_AGENTS[0]
    agent_name = agent_data["agent"]["name"]
    async with async_session() as session:
        result = await session.execute(select(Agent).where(Agent.name == agent_name))
        agent = result.scalar_one_or_none()
        if agent is None:
            return
        tools_result = await session.execute(select(AgentTool).where(AgentTool.agent_id == agent.id))
        if tools_result.scalars().first() is not None:
            return
        tool_map = await _create_tools(session, agent, agent_data["tools"])
        role_map = await _create_roles(session, agent, agent_data["roles"])
        await _assign_permissions(session, role_map, tool_map, agent_data["permissions"])
        await session.commit()
