"""Tests for PolicyCheckNode — RBAC tool filtering."""

from agent_runtime.application.runtime_access import resolve_effective_role
from agent_runtime.application.runtime.nodes.policy import policy_check_node
from agent_runtime.infrastructure.tools.registry import get_allowed_tools


class TestGetAllowedTools:
    def test_customer_tools(self):
        tools = get_allowed_tools("customer")
        assert "searchKnowledgeBase" in tools
        assert "getOrderStatus" in tools
        assert "getInternalSecrets" not in tools

    def test_admin_tools(self):
        tools = get_allowed_tools("admin")
        assert "searchKnowledgeBase" in tools
        assert "getOrderStatus" in tools
        assert "getInternalSecrets" in tools

    def test_unknown_role(self):
        tools = get_allowed_tools("hacker")
        assert tools == []


class TestPolicyCheckNode:
    def test_customer_state(self):
        state = {"user_role": "customer"}
        result = policy_check_node(state)
        assert "getInternalSecrets" not in result["allowed_tools"]
        assert "searchKnowledgeBase" in result["allowed_tools"]

    def test_admin_state(self):
        state = {"user_role": "admin"}
        result = policy_check_node(state)
        assert "getInternalSecrets" in result["allowed_tools"]


class TestRuntimeSpecRoleResolution:
    def test_known_runtime_role_is_used(self):
        spec = {"default_role": "customer", "roles": [{"name": "customer"}, {"name": "operator"}]}

        assert resolve_effective_role("operator", spec) == "operator"

    def test_missing_runtime_role_defaults_only_when_no_role_requested(self):
        spec = {"default_role": "customer", "roles": [{"name": "customer"}]}

        assert resolve_effective_role(None, spec) == "customer"

    def test_unknown_requested_runtime_role_does_not_fall_back_to_default(self):
        spec = {"default_role": "customer", "roles": [{"name": "customer"}]}

        assert resolve_effective_role("benchmark_no_tools", spec) == "benchmark_no_tools"
