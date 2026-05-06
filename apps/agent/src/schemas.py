"""Agent-Firewall Agent — Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    """POST /agent/chat request body."""

    message: str = Field(..., min_length=1, max_length=4096)
    user_role: str = Field(default="customer", min_length=1, max_length=128)
    session_id: str = Field(..., min_length=1, max_length=128)
    agent_id: str | None = Field(default=None, max_length=128)
    policy: str | None = Field(default=None, max_length=64, description="Policy name override (default: from config)")
    model: str | None = Field(default=None, max_length=128, description="Model override (default: from config)")


class OpenClawDirectRequest(BaseModel):
    """POST /agent/openclaw/direct request body."""

    message: str = Field(..., min_length=1, max_length=8192)
    session_id: str = Field(..., min_length=1, max_length=128)
    agent_id: str | None = Field(default=None, max_length=128)
    timeout_seconds: int | None = Field(default=None, ge=1, le=600)


class OpenClawDirectResponse(BaseModel):
    """Direct OpenClaw response used by Compare."""

    session_id: str
    response: str
    agent_id: str
    latency_ms: int


class OpenClawRuntimeDiagnostics(BaseModel):
    """Redacted local OpenClaw runtime diagnostics."""

    openclaw_bin: str
    openclaw_agent_id: str
    openclaw_agent_local: bool
    openclaw_timeout_seconds: int
    deepseek_configured: bool
    default_model: str
    default_model_prefix: str
    status_ok: bool = False
    models_ok: bool = False
    agents_ok: bool = False
    telegram_enabled: bool = False
    telegram_accounts: int = 0
    gateway_mode: str = "unknown"
    gateway_token_present: bool = False
    error: str | None = None


class ToolCallInfo(BaseModel):
    """Single tool call trace."""

    tool: str
    args: dict = Field(default_factory=dict)
    result_preview: str = ""
    allowed: bool = True
    blocked_reason: str | None = None


class AgentTrace(BaseModel):
    """Agent-level trace metadata."""

    agent_id: str = ""
    agent_name: str = ""
    agent_kind: str = ""
    parent_agent_id: str | None = None
    delegated_from: str | None = None
    delegated_to: str | None = None
    task: str | None = None
    tool_flow: list[dict] = Field(default_factory=list)
    intent: str = "unknown"
    user_role: str = "customer"
    allowed_tools: list[str] = Field(default_factory=list)
    available_sub_agents: list[str] = Field(default_factory=list)
    iterations: int = 0
    latency_ms: int = 0


class FirewallDecision(BaseModel):
    """Firewall decision from proxy-service."""

    decision: str = "UNKNOWN"
    risk_score: float = 0.0
    intent: str = ""
    risk_flags: dict = Field(default_factory=dict)
    blocked_reason: str | None = None


class AgentChatResponse(BaseModel):
    """POST /agent/chat response body."""

    response: str
    session_id: str
    tools_called: list[ToolCallInfo] = Field(default_factory=list)
    agent_trace: AgentTrace = Field(default_factory=AgentTrace)
    firewall_decision: FirewallDecision = Field(default_factory=FirewallDecision)
    trace: dict = Field(default_factory=dict, description="Structured agent trace (spec 07)")
