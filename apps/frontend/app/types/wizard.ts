// ─── Enums ───

export type AgentFramework = 'langgraph' | 'raw_python' | 'proxy_only'
export type AgentEnvironment = 'dev' | 'staging' | 'production'
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'
export type ProtectionLevel = 'proxy_only' | 'agent_runtime' | 'full'
export type RolloutMode = 'observe' | 'warn' | 'enforce'
export type AgentStatus = 'draft' | 'active' | 'archived'
export type AgentKind = 'main_agent' | 'sub_agent'
export type AgentCreatedFrom = 'manual' | 'sandbox_chat' | 'template'
export type AccessType = 'read' | 'write'
export type Sensitivity = 'low' | 'medium' | 'high' | 'critical'
export type SkillScope = 'main_agent' | 'sub_agent' | 'shared'
export type GateDecisionType = 'rbac' | 'injection' | 'pii' | 'budget'
export type GateAction = 'ALLOW' | 'DENY' | 'BLOCK' | 'REDACT' | 'WARN'
export type TraceGate = 'pre_tool' | 'post_tool' | 'pre_llm' | 'post_llm'
export type TraceDecision = 'ALLOW' | 'DENY' | 'REDACT' | 'WARN'
export type IncidentSeverity = 'low' | 'medium' | 'high' | 'critical'
export type IncidentCategory = 'rbac' | 'injection' | 'pii' | 'budget' | 'policy'
export type IncidentStatus = 'open' | 'acknowledged' | 'resolved' | 'false_positive'

// ─── Agent ───

export interface AgentCreate {
  name: string
  description?: string
  team?: string | null
  framework?: AgentFramework
  environment?: AgentEnvironment
  is_public_facing?: boolean
  has_tools?: boolean
  has_write_actions?: boolean
  touches_pii?: boolean
  handles_secrets?: boolean
  calls_external_apis?: boolean
  policy_pack?: string | null
  agent_kind?: AgentKind
  created_from?: AgentCreatedFrom
  template_key?: string | null
}

export interface AgentUpdate {
  name?: string
  description?: string
  team?: string | null
  framework?: AgentFramework
  environment?: AgentEnvironment
  is_public_facing?: boolean
  has_tools?: boolean
  has_write_actions?: boolean
  touches_pii?: boolean
  handles_secrets?: boolean
  calls_external_apis?: boolean
  status?: AgentStatus
  policy_pack?: string | null
  agent_kind?: AgentKind
  created_from?: AgentCreatedFrom
  template_key?: string | null
}

export interface AgentRead {
  id: string
  name: string
  description: string
  team: string | null
  framework: AgentFramework
  environment: AgentEnvironment
  is_public_facing: boolean
  has_tools: boolean
  has_write_actions: boolean
  touches_pii: boolean
  handles_secrets: boolean
  calls_external_apis: boolean
  risk_level: RiskLevel | null
  protection_level: ProtectionLevel | null
  policy_pack: string | null
  rollout_mode: RolloutMode
  status: AgentStatus
  is_reference: boolean
  agent_kind: AgentKind
  created_from: AgentCreatedFrom
  template_key: string | null
  generated_config: Record<string, unknown> | null
  generated_kit: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface AgentListResponse {
  items: AgentRead[]
  total: number
  page: number
  per_page: number
}

export interface AgentTeamSubAgent {
  agent: AgentRead
  binding: DelegationRead | null
  tools_count: number
  roles_count: number
  skills_count: number
  last_trace_at: string | null
}

export interface AgentTeamRead {
  main_agent: AgentRead
  sub_agents: AgentTeamSubAgent[]
  tools_count: number
  roles_count: number
  skills_count: number
  last_trace_at: string | null
}

export interface AgentTeamsResponse {
  items: AgentTeamRead[]
  total: number
}

export interface SubAgentCreateRequest {
  name: string
  description?: string
  team?: string | null
  framework?: AgentFramework
  environment?: AgentEnvironment
  policy_pack?: string | null
  template_key?: string | null
  delegation_description?: string
  when_to_delegate?: string
  sort_order?: number
  is_active?: boolean
}

export interface AgentTeamTemplateCreate {
  template_key: string
}

// ─── Tool ───

export interface ToolCreate {
  name: string
  description?: string
  category?: string | null
  access_type?: AccessType
  sensitivity?: Sensitivity
  arg_schema?: Record<string, unknown> | null
  returns_pii?: boolean
  returns_secrets?: boolean
  rate_limit?: number | null
}

export interface ToolUpdate {
  name?: string
  description?: string
  category?: string | null
  access_type?: AccessType
  sensitivity?: Sensitivity
  arg_schema?: Record<string, unknown> | null
  returns_pii?: boolean
  returns_secrets?: boolean
  rate_limit?: number | null
}

export interface ToolRead {
  id: string
  agent_id: string
  name: string
  description: string
  category: string | null
  access_type: AccessType
  sensitivity: Sensitivity
  requires_confirmation: boolean
  arg_schema: Record<string, unknown> | null
  returns_pii: boolean
  returns_secrets: boolean
  rate_limit: number | null
  created_at: string
  updated_at: string
}

export interface OpenClawSkillRead {
  name: string
  description: string
  source: string | null
  bundled: boolean
  eligible: boolean
  disabled: boolean
  blocked_by_allowlist: boolean
  emoji: string | null
  homepage: string | null
  missing: Record<string, unknown>
}

export interface OpenClawSkillsResponse {
  items: OpenClawSkillRead[]
}

export interface OpenClawAgentRead {
  id: string
  name: string
  workspace: string | null
  model: string | Record<string, unknown> | null
  bindings: number
  is_default: boolean
}

export interface OpenClawAgentsResponse {
  items: OpenClawAgentRead[]
}

export interface OpenClawHookRead {
  name: string
  description: string
  emoji: string | null
  eligible: boolean
  disabled: boolean
  enabled_by_config: boolean
  requirements_satisfied: boolean
  loadable: boolean
  source: string | null
  events: string[]
  homepage: string | null
  missing: Record<string, unknown>
  managed_by_plugin: boolean
}

export interface OpenClawHooksResponse {
  items: OpenClawHookRead[]
}

export interface OpenClawStatusResponse {
  status: Record<string, unknown>
  models: Record<string, unknown>
}

// ─── Role ───

export interface RoleCreate {
  name: string
  description?: string
  inherits_from?: string | null
}

export interface RoleUpdate {
  name?: string
  description?: string
  inherits_from?: string | null
}

export interface PermissionEntry {
  tool_id: string
  scopes?: string[]
  requires_confirmation_override?: boolean | null
  conditions?: Record<string, unknown> | null
}

export interface PermissionRead {
  id: string
  tool_id: string
  tool_name: string | null
  scopes: string[]
  requires_confirmation_override: boolean | null
  conditions: Record<string, unknown> | null
}

export interface RoleRead {
  id: string
  agent_id: string
  name: string
  description: string
  inherits_from: string | null
  permissions: PermissionRead[]
  inherited_permissions: PermissionRead[]
  created_at: string
}

export interface PermissionBatchSet {
  permissions: PermissionEntry[]
}

export interface PermissionMatrixResponse {
  tools: string[]
  roles: string[]
  matrix: Record<string, Record<string, string>>
}

export interface PermissionCheckResponse {
  allowed: boolean
  decision: string
  reason: string
}

// ─── Skills / Delegation ───

export interface SkillRead {
  id: string
  agent_id: string
  name: string
  description: string
  scope: SkillScope
  prompt_fragment: string
  constraints: Record<string, unknown> | null
  output_contract: Record<string, unknown> | null
  sort_order: number
  created_at: string
  updated_at: string
}

export interface DelegationRead {
  id: string
  parent_agent_id: string
  child_agent_id: string
  child_agent_name: string | null
  child_agent_description: string | null
  delegation_description: string
  when_to_delegate: string
  sort_order: number
  is_active: boolean
  created_at: string
  updated_at: string
}

// ─── Runtime Spec ───

export interface RuntimePermissionSpec {
  tool_name: string
  scopes: string[]
  decision: string
  sensitivity: Sensitivity
  requires_confirmation: boolean
}

export interface RuntimeRoleSpec {
  name: string
  description: string
  inherits_from: string | null
  permissions: RuntimePermissionSpec[]
  effective_tools: string[]
}

export interface RuntimeToolSpec {
  name: string
  description: string
  category: string | null
  provider_type: string
  provider_ref: string
  access_type: AccessType
  sensitivity: Sensitivity
  requires_confirmation: boolean
  arg_schema: Record<string, unknown> | null
  returns_pii: boolean
  returns_secrets: boolean
  pre_gate_enabled: boolean
  post_gate_enabled: boolean
  rate_limit: number | null
}

export interface RuntimeSkillSpec {
  name: string
  description: string
  scope: SkillScope
  prompt_fragment: string
  constraints: Record<string, unknown> | null
  output_contract: Record<string, unknown> | null
  sort_order: number
}

export interface RuntimeSubAgentSpec {
  agent_id: string
  openclaw_agent_id: string | null
  name: string
  description: string
  delegation_description: string
  when_to_delegate: string
  skills_summary: string[]
}

export interface AgentRuntimeSpec {
  agent_id: string
  name: string
  description: string
  agent_kind: AgentKind
  created_from: AgentCreatedFrom
  template_key: string | null
  framework: AgentFramework
  policy_pack: string | null
  default_role: string | null
  roles: RuntimeRoleSpec[]
  tools: RuntimeToolSpec[]
  skills: RuntimeSkillSpec[]
  sub_agents: RuntimeSubAgentSpec[]
  generated_config: Record<string, unknown> | null
}

// ─── Config ───

export interface GeneratedConfig {
  rbac_yaml: string
  limits_yaml: string
  policy_yaml: string
  generated_at: string
}

export interface PolicyPack {
  name: string
  description: string
  risk_levels: string[]
  [key: string]: unknown
}

// ─── Integration Kit ───

export interface IntegrationKit {
  files: Record<string, string>
  [key: string]: unknown
}

// ─── Validation ───

export interface ValidationTestResult {
  name: string
  category: string
  expected: string
  actual: string
  passed: boolean
  duration_ms: number
  recommendation?: string | null
  version?: string
}

export interface CategoryBreakdown {
  passed: number
  total: number
}

export interface ValidationResponse {
  agent_id: string
  pack: string
  pack_version: string
  score: number
  total: number
  passed: number
  failed: number
  categories: Record<string, CategoryBreakdown>
  tests: ValidationTestResult[]
  run_at: string
  duration_ms: number
}

export interface ValidationRunResults {
  categories: Record<string, CategoryBreakdown>
  tests: ValidationTestResult[]
  run_at: string
}

export interface ValidationRunRead {
  id: string
  agent_id: string
  pack: string
  pack_version?: string
  total: number
  passed: number
  failed: number
  score: number
  duration_ms?: number
  results: ValidationRunResults
  created_at: string
}

// ─── Rollout ───

export interface RolloutPromoteRequest {
  mode: RolloutMode
}

export interface RolloutPromoteResponse {
  id: string
  name: string
  rollout_mode: RolloutMode
  previous_mode: RolloutMode
}

export interface PromotionEventRead {
  id: string
  agent_id: string
  from_mode: RolloutMode
  to_mode: RolloutMode
  user: string
  created_at: string
}

export interface ReadinessStats {
  traces_in_current_mode: number
  would_have_blocked: number
  false_positive_rate: number | null
  latest_validation: Record<string, unknown> | null
}

export interface ReadinessResponse {
  current_mode: RolloutMode
  can_promote_to: RolloutMode[]
  blockers: string[]
  stats: ReadinessStats
}

// ─── Gate Decision ───

export interface GateEvalRequest {
  gate_type: GateDecisionType
  context?: Record<string, unknown> | null
}

export interface GateEvalResponse {
  decision: GateAction
  effective_action: GateAction
  rollout_mode: RolloutMode
  enforced: boolean
  warning: string | null
}

export interface GateDecisionRead {
  id: string
  agent_id: string
  gate_type: GateDecisionType
  decision: GateAction
  effective_action: GateAction
  rollout_mode: RolloutMode
  enforced: boolean
  warning: string | null
  context: Record<string, unknown> | null
  created_at: string
}

// ─── Traces ───

export interface TraceCreate {
  session_id?: string
  gate: TraceGate
  tool_name?: string | null
  role?: string | null
  decision: TraceDecision
  reason?: string
  category?: string
  rollout_mode?: RolloutMode
  enforced?: boolean
  latency_ms?: number
  details?: Record<string, unknown> | null
}

export interface TraceRead {
  id: string
  agent_id: string
  session_id: string
  timestamp: string
  gate: TraceGate
  tool_name: string | null
  role: string | null
  decision: TraceDecision
  reason: string
  category: string
  rollout_mode: RolloutMode
  enforced: boolean
  latency_ms: number
  details: Record<string, unknown> | null
  incident_id: string | null
}

export interface TraceListResponse {
  items: TraceRead[]
  total: number
  page: number
  per_page: number
}

// ─── Incidents ───

export interface IncidentRead {
  id: string
  agent_id: string
  severity: IncidentSeverity
  category: IncidentCategory
  title: string
  status: IncidentStatus
  first_seen: string
  last_seen: string
  trace_count: number
  details: Record<string, unknown> | null
}

export interface IncidentListResponse {
  items: IncidentRead[]
  total: number
}

export interface IncidentUpdate {
  status: IncidentStatus
}

export interface IncidentStatsBreakdown {
  open: number
  acknowledged: number
  resolved: number
  false_positive: number
}

export interface TraceStatsResponse {
  total_evaluations: number
  by_decision: Record<string, number>
  by_category: Record<string, number>
  by_gate: Record<string, number>
  avg_latency_ms: number
  incidents: IncidentStatsBreakdown
}
