"""Tests for the OpenClaw integration kit generator.

Covers:
  29a — Template engine + context builder (6 tests)
  29b — rbac.yaml template (4 tests)
  29c — limits.yaml template (4 tests)
  29d — policy.yaml template (4 tests)
  29e — OpenClaw wrapper
  29h — .env.protector (4 tests)
  29i — test_security.py (6 tests)
  29j — README.md (3 tests)
  29k — Kit API + download (9 tests)
  29l — End-to-end smoke
"""

from __future__ import annotations

import ast
import io
import uuid
import zipfile

import pytest
import yaml
from httpx import ASGITransport, AsyncClient

from src.control_plane.seed import REFERENCE_AGENT, seed_reference_agent, seed_reference_tools_and_roles
from src.control_plane.services.integration_kit import (
    build_kit_context,
    generate_integration_kit,
    get_jinja_env,
)
from src.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Helpers ──────────────────────────────────────────────────────────────

_AGENT_BODY = {
    "name": f"KitTestAgent-{uuid.uuid4().hex[:8]}",
    "description": "Agent for integration kit tests",
    "team": "platform",
    "framework": "openclaw",
    "environment": "dev",
    "is_public_facing": False,
    "has_tools": True,
    "has_write_actions": False,
    "touches_pii": False,
    "handles_secrets": False,
    "calls_external_apis": False,
}


async def _create_agent(client: AsyncClient, **overrides) -> dict:
    body = {**_AGENT_BODY, "name": f"KitAgent-{uuid.uuid4().hex[:8]}", **overrides}
    resp = await client.post("/v1/agents", json=body)
    assert resp.status_code == 201
    return resp.json()


async def _create_tool(client: AsyncClient, agent_id: str, **overrides) -> dict:
    body = {"name": f"tool-{uuid.uuid4().hex[:8]}", "description": "test tool", **overrides}
    resp = await client.post(f"/v1/agents/{agent_id}/tools", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_role(client: AsyncClient, agent_id: str, **overrides) -> dict:
    body = {"name": f"role-{uuid.uuid4().hex[:8]}", "description": "test role", **overrides}
    resp = await client.post(f"/v1/agents/{agent_id}/roles", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _seed_ref_agent(client: AsyncClient) -> dict:
    """Seed reference agent + tools/roles, return agent dict."""
    await seed_reference_agent()
    await seed_reference_tools_and_roles()
    resp = await client.get("/v1/agents", params={"status": "active"})
    ref = next(a for a in resp.json()["items"] if a["name"] == REFERENCE_AGENT["name"])
    await client.patch(f"/v1/agents/{ref['id']}", json={"policy_pack": "customer_support"})
    return ref


async def _create_agent_with_tools_roles(client: AsyncClient, framework: str = "openclaw") -> dict:
    """Create agent with 3 tools + 2 roles for testing."""
    agent = await _create_agent(client, framework=framework, policy_pack="customer_support")
    aid = agent["id"]

    t1 = await _create_tool(client, aid, name="readData", access_type="read", sensitivity="low")
    t2 = await _create_tool(client, aid, name="writeData", access_type="write", sensitivity="high")
    t3 = await _create_tool(client, aid, name="deleteAll", access_type="write", sensitivity="critical")

    r1 = await _create_role(client, aid, name="viewer", description="Read-only user")
    r2 = await _create_role(client, aid, name="editor", description="Can write", inherits_from=r1["id"])

    # Set permissions: viewer→readData, editor→writeData+deleteAll
    await client.put(
        f"/v1/agents/{aid}/roles/{r1['id']}/permissions",
        json={"permissions": [{"tool_id": t1["id"], "scopes": ["read"]}]},
    )
    await client.put(
        f"/v1/agents/{aid}/roles/{r2['id']}/permissions",
        json={
            "permissions": [
                {"tool_id": t2["id"], "scopes": ["read", "write"]},
                {"tool_id": t3["id"], "scopes": ["read", "write"]},
            ]
        },
    )

    return agent


# ═══════════════════════════════════════════════════════════════════════
# 29a — Template engine + context builder (6 tests)
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_jinja2_env_loads(client):
    """Jinja2 environment configured, templates dir exists."""
    env = get_jinja_env()
    assert env is not None
    # Should be able to list templates
    templates = env.loader.list_templates()
    assert len(templates) >= 4


@pytest.mark.asyncio
async def test_context_builder_demo_agent(client):
    """build_kit_context(demo_id) has all required keys."""
    ref = await _seed_ref_agent(client)
    from src.db.session import get_db

    async for db in get_db():
        ctx = await build_kit_context(uuid.UUID(ref["id"]), db)
        required_keys = [
            "agent_name",
            "agent_id",
            "framework",
            "tools",
            "roles",
            "policy_pack",
            "pack_config",
            "proxy_url",
            "generated_at",
        ]
        for key in required_keys:
            assert key in ctx, f"Missing key: {key}"
        break


@pytest.mark.asyncio
async def test_context_builder_tools_populated(client):
    """Context tools list matches DB tools."""
    ref = await _seed_ref_agent(client)
    from src.db.session import get_db

    async for db in get_db():
        ctx = await build_kit_context(uuid.UUID(ref["id"]), db)
        tool_names = {t["name"] for t in ctx["tools"]}
        assert tool_names
        assert all(name.startswith("openclaw_") for name in tool_names)
        break


@pytest.mark.asyncio
async def test_context_builder_roles_populated(client):
    """Context roles list matches DB roles."""
    ref = await _seed_ref_agent(client)
    from src.db.session import get_db

    async for db in get_db():
        ctx = await build_kit_context(uuid.UUID(ref["id"]), db)
        role_names = {r["name"] for r in ctx["roles"]}
        assert role_names == {"customer", "operator"}
        break


@pytest.mark.asyncio
async def test_context_builder_nonexistent_agent(client):
    """build_kit_context('bad-id') raises ValueError."""
    from src.db.session import get_db

    async for db in get_db():
        with pytest.raises(ValueError, match="not found"):
            await build_kit_context(uuid.uuid4(), db)
        break


@pytest.mark.asyncio
async def test_context_builder_agent_no_tools(client):
    """Agent with 0 tools → context.tools = [] (no crash)."""
    agent = await _create_agent(client)
    from src.db.session import get_db

    async for db in get_db():
        ctx = await build_kit_context(uuid.UUID(agent["id"]), db)
        assert ctx["tools"] == []
        break


# ═══════════════════════════════════════════════════════════════════════
# 29b — rbac.yaml template (4 tests)
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_rbac_template_renders(client):
    """rbac.yaml renders without error via kit."""
    ref = await _seed_ref_agent(client)
    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        assert "rbac.yaml" in kit["files"]
        assert len(kit["files"]["rbac.yaml"]) > 0
        break


@pytest.mark.asyncio
async def test_rbac_template_valid_yaml(client):
    """rbac.yaml output is parseable YAML."""
    ref = await _seed_ref_agent(client)
    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        data = yaml.safe_load(kit["files"]["rbac.yaml"])
        assert "roles" in data
        break


@pytest.mark.asyncio
async def test_rbac_template_matches_generator(client):
    """rbac.yaml from kit == direct generator output."""
    ref = await _seed_ref_agent(client)
    from src.control_plane.services.config_gen import generate_rbac_yaml
    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        direct = await generate_rbac_yaml(uuid.UUID(ref["id"]), db)
        # Compare parsed YAML (timestamps in comments may differ)
        assert yaml.safe_load(kit["files"]["rbac.yaml"]) == yaml.safe_load(direct)
        break


@pytest.mark.asyncio
async def test_rbac_template_empty_tools(client):
    """0 tools → valid YAML."""
    agent = await _create_agent(client)
    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(agent["id"]), db)
        data = yaml.safe_load(kit["files"]["rbac.yaml"])
        assert "roles" in data
        break


# ═══════════════════════════════════════════════════════════════════════
# 29c — limits.yaml template (4 tests)
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_limits_template_renders(client):
    """limits.yaml renders without error."""
    ref = await _seed_ref_agent(client)
    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        assert "limits.yaml" in kit["files"]
        break


@pytest.mark.asyncio
async def test_limits_template_valid_yaml(client):
    """limits.yaml is parseable YAML."""
    ref = await _seed_ref_agent(client)
    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        data = yaml.safe_load(kit["files"]["limits.yaml"])
        assert "roles" in data
        break


@pytest.mark.asyncio
async def test_limits_template_matches_generator(client):
    """limits.yaml from kit == direct generator output."""
    ref = await _seed_ref_agent(client)
    from src.control_plane.services.config_gen import generate_limits_yaml
    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        direct = await generate_limits_yaml(uuid.UUID(ref["id"]), db)
        assert yaml.safe_load(kit["files"]["limits.yaml"]) == yaml.safe_load(direct)
        break


@pytest.mark.asyncio
async def test_limits_template_per_tool_rates(client):
    """Per-tool rate_limit present when defined."""
    ref = await _seed_ref_agent(client)
    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        data = yaml.safe_load(kit["files"]["limits.yaml"])
        assert "tool_rate_limits" in data
        assert len(data["tool_rate_limits"]) > 0
        break


# ═══════════════════════════════════════════════════════════════════════
# 29d — policy.yaml template (4 tests)
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_policy_template_renders(client):
    """policy.yaml renders without error."""
    ref = await _seed_ref_agent(client)
    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        assert "policy.yaml" in kit["files"]
        break


@pytest.mark.asyncio
async def test_policy_template_valid_yaml(client):
    """policy.yaml is parseable YAML."""
    ref = await _seed_ref_agent(client)
    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        data = yaml.safe_load(kit["files"]["policy.yaml"])
        assert "scanners" in data
        break


@pytest.mark.asyncio
async def test_policy_template_matches_generator(client):
    """policy.yaml from kit == direct generator output."""
    ref = await _seed_ref_agent(client)
    from src.control_plane.services.config_gen import generate_policy_yaml
    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        direct = await generate_policy_yaml(uuid.UUID(ref["id"]), db)
        assert yaml.safe_load(kit["files"]["policy.yaml"]) == yaml.safe_load(direct)
        break


@pytest.mark.asyncio
async def test_policy_template_all_scanners(client):
    """All scanner toggles present in policy.yaml."""
    ref = await _seed_ref_agent(client)
    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        data = yaml.safe_load(kit["files"]["policy.yaml"])
        for key in ["injection_detection", "pii_redaction", "secrets_scanning", "toxicity_detection"]:
            assert key in data["scanners"], f"Missing scanner: {key}"
        break


# ═══════════════════════════════════════════════════════════════════════
# 29e — OpenClaw wrapper
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_openclaw_template_renders(client):
    """OpenClaw template renders without error."""
    ref = await _seed_ref_agent(client)
    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        assert "protected_agent.py" in kit["files"]
        assert kit["framework"] == "openclaw"
        assert len(kit["files"]["protected_agent.py"]) > 100
        break


@pytest.mark.asyncio
async def test_openclaw_ast_parse(client):
    """ast.parse(output) — syntactically valid Python."""
    ref = await _seed_ref_agent(client)
    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        code = kit["files"]["protected_agent.py"]
        tree = ast.parse(code)
        assert tree is not None
        break


@pytest.mark.asyncio
async def test_openclaw_uses_agent_firewall_base_url(client):
    """OpenClaw integration routes through Agent-Firewall."""
    ref = await _seed_ref_agent(client)
    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        code = kit["files"]["protected_agent.py"]
        assert "AGENT_FIREWALL_URL" in code
        assert 'base_url=f"{AGENT_FIREWALL_URL}/v1"' in code
        break


@pytest.mark.asyncio
async def test_openclaw_imports_openai_client(client):
    """OpenClaw kit exposes an OpenAI-compatible client pointing at the firewall."""
    ref = await _seed_ref_agent(client)
    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        code = kit["files"]["protected_agent.py"]
        assert "from openai import OpenAI" in code
        assert "client = OpenAI(" in code
        break


@pytest.mark.asyncio
async def test_openclaw_has_firewall_runtime_comment(client):
    """Generated OpenClaw kit names the protected runtime route."""
    ref = await _seed_ref_agent(client)
    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        code = kit["files"]["protected_agent.py"]
        assert "Agent-Firewall" in code
        assert "OpenClaw" in code
        break


@pytest.mark.asyncio
async def test_openclaw_tool_names_stay_in_yaml(client):
    """Agent tool names are represented in generated policy YAML, not framework code."""
    ref = await _seed_ref_agent(client)
    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        rbac = yaml.safe_load(kit["files"]["rbac.yaml"])
        all_tools = {tool_name for role in rbac.get("roles", {}).values() for tool_name in role.get("tools", {})}
        assert all_tools
        assert all(name.startswith("openclaw_") for name in all_tools)
        break


@pytest.mark.asyncio
async def test_openclaw_role_names_stay_in_yaml(client):
    """Agent role names are represented in RBAC YAML."""
    ref = await _seed_ref_agent(client)
    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        rbac = yaml.safe_load(kit["files"]["rbac.yaml"])
        assert {"customer", "operator"} <= set(rbac.get("roles", {}))
        break


@pytest.mark.asyncio
async def test_openclaw_has_inline_comments(client):
    """≥5 inline comments present."""
    ref = await _seed_ref_agent(client)
    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        code = kit["files"]["protected_agent.py"]
        comment_lines = [line for line in code.splitlines() if line.strip().startswith("#")]
        assert len(comment_lines) >= 5
        break


# ═══════════════════════════════════════════════════════════════════════
# 29h — .env.protector (4 tests)
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_env_template_renders(client):
    """Template renders without error."""
    ref = await _seed_ref_agent(client)

    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        assert ".env.protector" in kit["files"]
        break


@pytest.mark.asyncio
async def test_env_parseable(client):
    """python-dotenv can parse output."""
    from dotenv import dotenv_values

    ref = await _seed_ref_agent(client)

    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        content = kit["files"][".env.protector"]
        # dotenv_values can parse from a stream
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(content)
            f.flush()
            values = dotenv_values(f.name)
        assert "AGENT_FIREWALL_URL" in values
        assert "AGENT_FIREWALL_AGENT_ID" in values
        break


@pytest.mark.asyncio
async def test_env_has_required_vars(client):
    """AGENT_FIREWALL_URL, AGENT_ID, POLICY, MODE present."""
    ref = await _seed_ref_agent(client)

    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        content = kit["files"][".env.protector"]
        for var in ["AGENT_FIREWALL_URL", "AGENT_FIREWALL_AGENT_ID", "AGENT_FIREWALL_POLICY", "AGENT_FIREWALL_MODE"]:
            assert var in content, f"Missing env var: {var}"
        break


@pytest.mark.asyncio
async def test_env_provider_key_commented(client):
    """DEEPSEEK_API_KEY is documented but commented out."""
    ref = await _seed_ref_agent(client)

    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        content = kit["files"][".env.protector"]
        for line in content.splitlines():
            if "DEEPSEEK_API_KEY" in line:
                assert line.strip().startswith("#"), "DEEPSEEK_API_KEY should be commented"
        break


# ═══════════════════════════════════════════════════════════════════════
# 29i — test_security.py template (6 tests)
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_security_template_renders(client):
    """Template renders without error."""
    ref = await _seed_ref_agent(client)

    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        assert "test_security.py" in kit["files"]
        break


@pytest.mark.asyncio
async def test_security_ast_parse(client):
    """ast.parse(output) — syntactically valid Python."""
    ref = await _seed_ref_agent(client)

    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        code = kit["files"]["test_security.py"]
        tree = ast.parse(code)
        assert tree is not None
        break


@pytest.mark.asyncio
async def test_security_has_5_test_functions(client):
    """5 functions starting with test_."""
    ref = await _seed_ref_agent(client)

    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        code = kit["files"]["test_security.py"]
        tree = ast.parse(code)
        test_funcs = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        ]
        assert len(test_funcs) == 5, f"Expected 5 test functions, got {len(test_funcs)}: {test_funcs}"
        break


@pytest.mark.asyncio
async def test_security_rbac_test_uses_agent_roles(client):
    """Test has unknown-role block + authorized-role check."""
    ref = await _seed_ref_agent(client)

    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        code = kit["files"]["test_security.py"]
        # Must test unknown role denial
        assert "__nonexistent_role__" in code
        # Must test authorized roles from RBAC config
        assert "test_rbac_allow_authorized" in code
        break


@pytest.mark.asyncio
async def test_security_injection_test_uses_agent_tool(client):
    """Test references injection detection config."""
    ref = await _seed_ref_agent(client)

    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        code = kit["files"]["test_security.py"]
        assert "injection" in code.lower()
        break


@pytest.mark.asyncio
async def test_security_pii_test_present(client):
    """PII redaction test function present."""
    ref = await _seed_ref_agent(client)

    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        code = kit["files"]["test_security.py"]
        assert "test_pii_redaction" in code
        break


# ═══════════════════════════════════════════════════════════════════════
# 29j — README.md template (3 tests)
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_readme_template_renders(client):
    """Template renders without error."""
    ref = await _seed_ref_agent(client)

    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        assert "README.md" in kit["files"]
        assert len(kit["files"]["README.md"]) > 100
        break


@pytest.mark.asyncio
async def test_readme_has_agent_name(client):
    """Agent name appears in rendered README."""
    ref = await _seed_ref_agent(client)

    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        assert REFERENCE_AGENT["name"] in kit["files"]["README.md"]
        break


@pytest.mark.asyncio
async def test_readme_has_integration_steps(client):
    """Step 1, Step 2, Step 3 present."""
    ref = await _seed_ref_agent(client)

    from src.db.session import get_db

    async for db in get_db():
        kit = await generate_integration_kit(uuid.UUID(ref["id"]), db)
        readme = kit["files"]["README.md"]
        assert "Step 1" in readme
        assert "Step 2" in readme
        assert "Step 3" in readme
        break


# ═══════════════════════════════════════════════════════════════════════
# 29k — Kit API + download (9 tests)
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_kit_post_returns_7_files(client):
    """POST → response.files has 7 keys."""
    ref = await _seed_ref_agent(client)
    resp = await client.post(f"/v1/agents/{ref['id']}/integration-kit")
    assert resp.status_code == 200
    data = resp.json()
    assert "files" in data
    assert len(data["files"]) == 7


@pytest.mark.asyncio
async def test_kit_post_nonexistent_agent(client):
    """POST bad ID → 404."""
    resp = await client.post(f"/v1/agents/{uuid.uuid4()}/integration-kit")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_kit_post_agent_no_tools(client):
    """POST agent with 0 tools → still generates (minimal kit)."""
    agent = await _create_agent(client)
    resp = await client.post(f"/v1/agents/{agent['id']}/integration-kit")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["files"]) == 7


@pytest.mark.asyncio
async def test_kit_download_returns_zip(client):
    """GET → Content-Type=application/zip."""
    ref = await _seed_ref_agent(client)
    await client.post(f"/v1/agents/{ref['id']}/integration-kit")
    resp = await client.get(f"/v1/agents/{ref['id']}/integration-kit/download")
    assert resp.status_code == 200
    assert "application/zip" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_kit_download_zip_has_7_files(client):
    """Unzip → 7 files."""
    ref = await _seed_ref_agent(client)
    await client.post(f"/v1/agents/{ref['id']}/integration-kit")
    resp = await client.get(f"/v1/agents/{ref['id']}/integration-kit/download")
    buf = io.BytesIO(resp.content)
    with zipfile.ZipFile(buf) as zf:
        assert len(zf.namelist()) == 7


@pytest.mark.asyncio
async def test_kit_download_filename_slugified(client):
    """Filename = agent-firewall-{slug}.zip."""
    ref = await _seed_ref_agent(client)
    await client.post(f"/v1/agents/{ref['id']}/integration-kit")
    resp = await client.get(f"/v1/agents/{ref['id']}/integration-kit/download")
    cd = resp.headers.get("content-disposition", "")
    assert "agent-firewall-" in cd
    assert ".zip" in cd


@pytest.mark.asyncio
async def test_kit_stores_on_agent(client):
    """After POST, agent record has last_kit JSONB."""
    ref = await _seed_ref_agent(client)
    await client.post(f"/v1/agents/{ref['id']}/integration-kit")
    resp = await client.get(f"/v1/agents/{ref['id']}/integration-kit")
    assert resp.status_code == 200
    assert "files" in resp.json()


@pytest.mark.asyncio
async def test_kit_framework_is_openclaw(client):
    """Generated kits always identify OpenClaw as the framework."""
    agent = await _create_agent(client, policy_pack="customer_support")
    await _create_tool(client, agent["id"], name="toolA")

    resp = await client.post(f"/v1/agents/{agent['id']}/integration-kit")

    assert resp.status_code == 200
    assert resp.json()["framework"] == "openclaw"
    assert "OpenClaw" in resp.json()["files"]["protected_agent.py"]


# ═══════════════════════════════════════════════════════════════════════
# 29l — End-to-end smoke
# ═══════════════════════════════════════════════════════════════════════


async def _e2e_flow(client: AsyncClient, framework: str) -> None:
    """Run full e2e: create agent → tools → roles → kit → extract → validate."""
    agent = await _create_agent_with_tools_roles(client, framework=framework)
    aid = agent["id"]

    # Generate kit
    resp = await client.post(f"/v1/agents/{aid}/integration-kit")
    assert resp.status_code == 200
    kit = resp.json()
    assert len(kit["files"]) == 7

    # Download ZIP
    resp = await client.get(f"/v1/agents/{aid}/integration-kit/download")
    assert resp.status_code == 200
    buf = io.BytesIO(resp.content)

    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
        assert len(names) == 7

        # Validate YAML files
        for yaml_file in ["rbac.yaml", "limits.yaml", "policy.yaml"]:
            content = zf.read(yaml_file).decode()
            data = yaml.safe_load(content)
            assert data is not None, f"{yaml_file} parsed to None"

        # Validate Python files
        py_file = zf.read("protected_agent.py").decode()
        ast.parse(py_file)  # must not raise

        test_file = zf.read("test_security.py").decode()
        tree = ast.parse(test_file)  # must not raise
        test_funcs = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        ]
        assert len(test_funcs) == 5

        # Validate .env.protector
        env_content = zf.read(".env.protector").decode()
        assert "AGENT_FIREWALL_URL" in env_content

        # Validate README
        readme = zf.read("README.md").decode()
        assert agent["name"] in readme


@pytest.mark.asyncio
async def test_e2e_openclaw(client):
    """Full e2e with OpenClaw framework."""
    await _e2e_flow(client, "openclaw")
