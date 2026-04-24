// ─── Agent runtime types ───

export interface AgentChatRequest {
  message: string
  user_role: string
  session_id: string
  agent_id?: string | null
  policy?: string
  model?: string
}

export interface ToolCall {
  tool: string
  args: Record<string, unknown>
  result_preview: string
  allowed: boolean
  blocked_reason?: string | null
}

export interface AgentTrace {
  agent_id: string
  agent_name: string
  intent: string
  user_role: string
  allowed_tools: string[]
  available_sub_agents: string[]
  iterations: number
  latency_ms: number
}

export interface FirewallDecision {
  decision: 'ALLOW' | 'MODIFY' | 'BLOCK' | 'UNKNOWN'
  risk_score: number
  intent: string
  risk_flags: Record<string, unknown>
  blocked_reason?: string | null
}

export interface AgentChatResponse {
  response: string
  session_id: string
  tools_called: ToolCall[]
  agent_trace: AgentTrace
  firewall_decision: FirewallDecision
}

export interface AgentMessageBlock {
  type: 'text' | 'tool'
  content?: string
  tool?: ToolCall
}

export interface AgentMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  blocks?: AgentMessageBlock[]
  tools_called?: ToolCall[]
  agent_trace?: AgentTrace
  firewall_decision?: FirewallDecision
  timestamp: Date
}
