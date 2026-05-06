/**
 * OpenClaw Compare.
 *
 * Left side: Agent-Firewall protected OpenClaw path (/agent/chat).
 * Right side: direct OpenClaw path (/agent/openclaw/direct), bypassing scan and gates.
 */
import { computed, reactive, ref } from 'vue'
import { agentService } from '~/services/agentService'
import type { ChatMessage, PipelineDecision } from '~/types/api'
import type { AgentChatResponse, ToolCall } from '~/types/agent'

export interface CompareTimings {
  protected: number | null
  direct: number | null
}

export type ComparePhase = 'idle' | 'streaming'

function generateSessionId(prefix: string) {
  return `${prefix}-${crypto.randomUUID()}`
}

function decisionFromAgent(response: AgentChatResponse): PipelineDecision {
  const fw = response.firewall_decision
  return {
    decision: fw.decision === 'UNKNOWN' ? 'ALLOW' : fw.decision,
    intent: fw.intent || response.agent_trace?.intent || 'unknown',
    riskScore: fw.risk_score ?? 0,
    riskFlags: fw.risk_flags ?? {},
    blockedReason: fw.blocked_reason ?? undefined,
  }
}

function toolSummary(tools: ToolCall[] = []) {
  if (!tools.length) return ''
  return `\n\nTools: ${tools
    .map((tool) => `${tool.allowed ? 'allowed' : 'blocked'} ${tool.tool}`)
    .join(', ')}`
}

export function useCompareChat() {
  const protectedMessages = ref<ChatMessage[]>([])
  const directMessages = ref<ChatMessage[]>([])
  const isProtectedStreaming = ref(false)
  const isDirectStreaming = ref(false)
  const protectedDecision = ref<PipelineDecision | null>(null)
  const timings = reactive<CompareTimings>({ protected: null, direct: null })
  const error = ref<string | null>(null)
  const phase = ref<ComparePhase>('idle')

  const protectedSessionId = ref(generateSessionId('compare-protected'))
  const directSessionId = ref(generateSessionId('compare-direct'))

  const config = reactive({
    policy: 'balanced',
    model: 'deepseek-chat',
    temperature: 0.7,
    maxTokens: null as number | null,
    agentId: null as string | null,
    openClawAgentId: null as string | null,
  })

  const isBusy = computed(() => phase.value !== 'idle')
  const directEndpointUrl = computed(() => '/agent/openclaw/direct')

  async function send(text: string) {
    const userMsg: ChatMessage = { role: 'user', content: text }
    protectedMessages.value.push({ ...userMsg })
    directMessages.value.push({ ...userMsg })
    protectedMessages.value.push({ role: 'assistant', content: '' })
    directMessages.value.push({ role: 'assistant', content: '' })

    const protIdx = protectedMessages.value.length - 1
    const dirIdx = directMessages.value.length - 1

    error.value = null
    protectedDecision.value = null
    timings.protected = null
    timings.direct = null
    phase.value = 'streaming'
    isProtectedStreaming.value = true
    isDirectStreaming.value = true

    const runProtected = async () => {
      const started = performance.now()
      try {
        const response = await agentService.chat({
          message: text,
          user_role: 'customer',
          session_id: protectedSessionId.value,
          agent_id: config.agentId,
          model: config.model,
          policy: config.policy,
        })
        protectedDecision.value = decisionFromAgent(response)
        protectedMessages.value[protIdx] = {
          role: 'assistant',
          content: `${response.response}${toolSummary(response.tools_called)}`,
          decision: protectedDecision.value,
          tools_called: response.tools_called,
        }
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err)
        protectedMessages.value[protIdx] = {
          role: 'assistant',
          content: `Blocked: ${message}`,
        }
        error.value = `Protected: ${message}`
      } finally {
        timings.protected = Math.round(performance.now() - started)
        isProtectedStreaming.value = false
      }
    }

    const runDirect = async () => {
      const started = performance.now()
      try {
        const response = await agentService.directOpenClaw({
          message: text,
          session_id: directSessionId.value,
          agent_id: config.openClawAgentId,
        })
        directMessages.value[dirIdx] = {
          role: 'assistant',
          content: response.response,
        }
        timings.direct = response.latency_ms || Math.round(performance.now() - started)
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err)
        directMessages.value[dirIdx] = {
          role: 'assistant',
          content: `Direct error: ${message}`,
        }
        if (!error.value) error.value = `Direct: ${message}`
        timings.direct = Math.round(performance.now() - started)
      } finally {
        isDirectStreaming.value = false
      }
    }

    await Promise.allSettled([runProtected(), runDirect()])
    phase.value = 'idle'
  }

  function clear() {
    protectedMessages.value = []
    directMessages.value = []
    protectedDecision.value = null
    timings.protected = null
    timings.direct = null
    error.value = null
    protectedSessionId.value = generateSessionId('compare-protected')
    directSessionId.value = generateSessionId('compare-direct')
  }

  function abort() {
    isProtectedStreaming.value = false
    isDirectStreaming.value = false
    phase.value = 'idle'
  }

  return {
    protectedMessages,
    directMessages,
    isProtectedStreaming,
    isDirectStreaming,
    protectedDecision,
    timings,
    error,
    config,
    phase,
    isBusy,
    directEndpointUrl,
    send,
    clear,
    abort,
  }
}
