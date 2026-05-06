import axios from 'axios'
import type { AxiosInstance } from 'axios'
import type { AgentChatRequest, AgentChatResponse } from '~/types/agent'
import { detectProviderClient, getKey } from '~/composables/useApiKeys'

const baseURL = import.meta.env.NUXT_PUBLIC_AGENT_API_BASE ?? 'http://localhost:8002'

export interface AgentStreamEvent {
  event: string
  data: Record<string, unknown>
}

const agentApi: AxiosInstance = axios.create({
  baseURL,
  timeout: 60_000,
  headers: { 'Content-Type': 'application/json' },
})

agentApi.interceptors.request.use((config) => {
  config.headers['x-correlation-id'] = crypto.randomUUID()
  return config
})

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
      'x-correlation-id': crypto.randomUUID()
    }

    if (request.model) {
      const provider = detectProviderClient(request.model)
      const apiKey = getKey(provider)
      if (apiKey) {
        headers['x-api-key'] = apiKey
      }
    }

    const response = await fetch(`${baseURL}/agent/chat`, {
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

    if (!response.body) {
      throw new Error('No response body')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''
      
      for (const chunk of lines) {
        if (!chunk.trim()) continue
        const eventMatch = chunk.match(/event:\s*(.+)/)
        const dataMatch = chunk.match(/data:\s*(.+)/)
        
        if (eventMatch && dataMatch) {
          const event = eventMatch[1].trim()
          try {
            const data = JSON.parse(dataMatch[1].trim())
            yield { event, data }
          }
          catch {
            console.error('Failed to parse SSE data:', dataMatch[1])
          }
        }
      }
    }
  },
}
