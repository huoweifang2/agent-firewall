import axios from 'axios'
import type { AxiosInstance } from 'axios'
import type { AgentChatRequest, AgentChatResponse } from '~/types/agent'
import { detectProviderClient, getKey } from '~/composables/useApiKeys'

const baseURL = import.meta.env.NUXT_PUBLIC_AGENT_API_BASE ?? 'http://localhost:8002'

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
  async chat(request: AgentChatRequest): Promise<AgentChatResponse> {
    const headers: Record<string, string> = {}

    // Inject API key for external providers
    if (request.model) {
      const provider = detectProviderClient(request.model)
      if (true) {
        const apiKey = getKey(provider)
        if (apiKey) {
          headers['x-api-key'] = apiKey
        }
      }
    }

    const { data } = await agentApi.post<AgentChatResponse>('/agent/chat', request, { headers })
    return data
  },

  async *streamChat(request: AgentChatRequest): AsyncGenerator<{ event: string; data: any }> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      'x-correlation-id': crypto.randomUUID()
    }

    if (request.model) {
      const provider = detectProviderClient(request.model)
      if (provider) {
        const apiKey = getKey(provider)
        if (apiKey) {
          headers['x-api-key'] = apiKey
        }
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
      } catch {}
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
          } catch (e) {
            console.error('Failed to parse SSE data:', dataMatch[1])
          }
        }
      }
    }
  },
}
