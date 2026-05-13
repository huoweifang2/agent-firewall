import type { AgentChatRequest, AgentChatResponse } from '~/types/agent'
import { detectProviderClient, getKey } from '~/composables/useApiKeys'
import { AGENT_API_BASE_URL, createCorrelatedJsonClient, newCorrelationId } from '~/services/http'
import { readJsonSseEvents } from '~/services/sse'

export interface AgentStreamEvent {
  event: string
  data: Record<string, unknown>
}

const agentApi = createCorrelatedJsonClient(AGENT_API_BASE_URL, 60_000)

export const agentService = {
  async getOpenClawConfig(): Promise<{
    openclaw_bin: string
    openclaw_agent_id: string
    openclaw_agent_local: boolean
    openclaw_timeout_seconds: number
    openclaw_plugin_stage_dir: string
    deepseek_configured: boolean
    default_model: string
    default_model_prefix: string
    status_ok: boolean
    models_ok: boolean
    agents_ok: boolean
    telegram_enabled: boolean
    telegram_accounts: number
    telegram_bridge_enabled: boolean
    telegram_bridge_running: boolean
    telegram_bridge_accounts: number
    telegram_bridge_last_error?: string | null
    gateway_mode: string
    gateway_token_present: boolean
    error?: string | null
  }> {
    const { data } = await agentApi.get('/agent/openclaw/config')
    return data
  },

  async directOpenClaw(request: {
    message: string
    session_id: string
    agent_id?: string | null
    timeout_seconds?: number
  }): Promise<{
    response: string
    session_id: string
    agent_id: string
    latency_ms: number
  }> {
    const { data } = await agentApi.post('/agent/openclaw/direct', request)
    return data
  },

  async chat(request: AgentChatRequest): Promise<AgentChatResponse> {
    const headers: Record<string, string> = {}

    // Inject API key for external providers
    if (request.model) {
      const provider = detectProviderClient(request.model)
      const apiKey = getKey(provider)
      if (apiKey) {
        headers['x-api-key'] = apiKey
      }
    }

    const { data } = await agentApi.post<AgentChatResponse>('/agent/chat', request, { headers })
    return data
  },

  async *streamChat(request: AgentChatRequest): AsyncGenerator<AgentStreamEvent> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      'x-correlation-id': newCorrelationId(),
    }

    if (request.model) {
      const provider = detectProviderClient(request.model)
      const apiKey = getKey(provider)
      if (apiKey) {
        headers['x-api-key'] = apiKey
      }
    }

    const response = await fetch(`${AGENT_API_BASE_URL}/agent/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify(request)
    })

    if (!response.ok) {
      let errText = response.statusText
      try {
        const errData = await response.json()
        errText = errData.detail || errText
      }
      catch {
        errText = response.statusText
      }
      throw new Error(`Chat API failed: ${response.status} ${errText}`)
    }

    for await (const event of readJsonSseEvents(response)) {
      yield event
    }
  },
}
