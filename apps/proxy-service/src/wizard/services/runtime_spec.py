"""Runtime spec builder for agent execution."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import set_committed_value

from src.wizard.models import Agent, AgentDelegation, AgentRole, AgentSkill, AgentTool, RoleToolPermission
from src.wizard.schemas import (
    AgentRuntimeSpec,
    RuntimePermissionSpec,
    RuntimeRoleSpec,
    RuntimeSkillSpec,
    RuntimeSubAgentSpec,
    RuntimeToolSpec,
)
from src.wizard.services.permissions import resolve_permissions_for_role

_KNOWN_PROVIDER_TYPES = {"internal", "composio", "mcp"}


async def _load_agent(agent_id: uuid.UUID, db: AsyncSession) -> Agent:
    agent = await db.get(Agent, agent_id)
    if agent is None:
        raise ValueError(f"Agent {agent_id} not found")
    return agent


async def _load_tools(agent_id: uuid.UUID, db: AsyncSession) -> list[AgentTool]:
    result = await db.execute(select(AgentTool).where(AgentTool.agent_id == agent_id).order_by(AgentTool.name))
    return list(result.scalars().all())


async def _load_roles(agent_id: uuid.UUID, db: AsyncSession) -> list[AgentRole]:
    result = await db.execute(
        select(AgentRole)
        .where(AgentRole.agent_id == agent_id)
        .options(selectinload(AgentRole.permissions).selectinload(RoleToolPermission.tool))
        .order_by(AgentRole.name)
    )
    roles = list(result.scalars().unique().all())
    role_by_id = {role.id: role for role in roles}
    for role in roles:
        parent = role_by_id.get(role.inherits_from) if role.inherits_from else None
        set_committed_value(role, "parent", parent)
    return roles


async def _load_skills(agent_id: uuid.UUID, db: AsyncSession) -> list[AgentSkill]:
    result = await db.execute(
        select(AgentSkill).where(AgentSkill.agent_id == agent_id).order_by(AgentSkill.sort_order, AgentSkill.name)
    )
    return list(result.scalars().all())


async def _load_delegations(agent_id: uuid.UUID, db: AsyncSession) -> list[AgentDelegation]:
    result = await db.execute(
        select(AgentDelegation)
        .where(AgentDelegation.parent_agent_id == agent_id, AgentDelegation.is_active == True)  # noqa: E712
        .options(selectinload(AgentDelegation.child_agent))
        .order_by(AgentDelegation.sort_order, AgentDelegation.created_at)
    )
    return list(result.scalars().unique().all())


def _infer_provider_type(tool: AgentTool) -> str:
    category = (tool.category or "").strip().lower()
    if category in _KNOWN_PROVIDER_TYPES:
        return category
    if tool.name.startswith("COMPOSIO_"):
        return "composio"
    return "internal"


def _provider_ref(tool: AgentTool, provider_type: str) -> str:
    schema = tool.arg_schema or {}
    provider = schema.get("provider") if isinstance(schema, dict) else None
    if isinstance(provider, dict):
        ref = provider.get("ref") or provider.get("tool_name")
        if isinstance(ref, str) and ref:
            return ref
    if provider_type == "composio":
        return tool.name
    if provider_type == "mcp":
        return tool.name
    return tool.name


def _sort_roles_by_depth(roles: list[AgentRole]) -> list[AgentRole]:
    depth: dict[uuid.UUID, int] = {}

    def _get_depth(role: AgentRole, visited: set[uuid.UUID] | None = None) -> int:
        if visited is None:
            visited = set()
        if role.id in visited:
            return 99
        if role.id in depth:
            return depth[role.id]
        visited.add(role.id)
        if role.parent is None:
            depth[role.id] = 0
        else:
            depth[role.id] = _get_depth(role.parent, visited) + 1
        return depth[role.id]

    for role in roles:
        _get_depth(role)

    return sorted(roles, key=lambda role: (depth.get(role.id, 0), role.name))


def _role_spec(role: AgentRole) -> RuntimeRoleSpec:
    own_permissions, inherited_permissions = resolve_permissions_for_role(role)
    all_permissions = [*own_permissions, *inherited_permissions]
    permission_specs: list[RuntimePermissionSpec] = []

    for perm in all_permissions:
        tool = perm.tool
        if tool is None:
            continue
        requires_confirmation = (
            perm.requires_confirmation_override
            if perm.requires_confirmation_override is not None
            else tool.requires_confirmation
        )
        decision = "confirm" if requires_confirmation else "allow"
        permission_specs.append(
            RuntimePermissionSpec(
                tool_name=tool.name,
                scopes=list(perm.scopes),
                decision=decision,
                sensitivity=tool.sensitivity,
                requires_confirmation=requires_confirmation,
            )
        )

    permission_specs.sort(key=lambda item: item.tool_name)
    return RuntimeRoleSpec(
        name=role.name,
        description=role.description,
        inherits_from=role.parent.name if role.parent else None,
        permissions=permission_specs,
        effective_tools=[perm.tool_name for perm in permission_specs],
    )


async def build_agent_runtime_spec(agent_id: uuid.UUID, db: AsyncSession) -> AgentRuntimeSpec:
    """Build the runtime spec that agent-runtime consumes."""
    agent = await _load_agent(agent_id, db)
    roles = _sort_roles_by_depth(await _load_roles(agent_id, db))
    tools = await _load_tools(agent_id, db)
    skills = await _load_skills(agent_id, db)
    delegations = await _load_delegations(agent_id, db)

    role_specs = [_role_spec(role) for role in roles]
    tool_specs = [
        RuntimeToolSpec(
            name=tool.name,
            description=tool.description,
            category=tool.category,
            provider_type=_infer_provider_type(tool),
            provider_ref=_provider_ref(tool, _infer_provider_type(tool)),
            access_type=tool.access_type,
            sensitivity=tool.sensitivity,
            requires_confirmation=tool.requires_confirmation,
            arg_schema=tool.arg_schema,
            returns_pii=tool.returns_pii,
            returns_secrets=tool.returns_secrets,
            rate_limit=tool.rate_limit,
        )
        for tool in tools
    ]
    skill_specs = [
        RuntimeSkillSpec(
            name=skill.name,
            description=skill.description,
            scope=skill.scope,
            prompt_fragment=skill.prompt_fragment,
            constraints=skill.constraints,
            output_contract=skill.output_contract,
            sort_order=skill.sort_order,
        )
        for skill in skills
    ]

    sub_agents: list[RuntimeSubAgentSpec] = []
    for delegation in delegations:
        child = delegation.child_agent
        if child is None:
            continue
        child_skills = await _load_skills(child.id, db)
        sub_agents.append(
            RuntimeSubAgentSpec(
                agent_id=child.id,
                name=child.name,
                description=child.description,
                delegation_description=delegation.delegation_description,
                when_to_delegate=delegation.when_to_delegate,
                skills_summary=[skill.name for skill in child_skills],
            )
        )

    default_role = role_specs[0].name if role_specs else None
    return AgentRuntimeSpec(
        agent_id=agent.id,
        name=agent.name,
        description=agent.description,
        framework=agent.framework,
        policy_pack=agent.policy_pack,
        default_role=default_role,
        roles=role_specs,
        tools=tool_specs,
        skills=skill_specs,
        sub_agents=sub_agents,
        generated_config=agent.generated_config,
    )
