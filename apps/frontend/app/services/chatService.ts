import { api } from './api'
import { API_BASE_URL } from './http'
import { consumeOpenAIStream } from './sse'
import { detectProviderClient, getKey } from '~/composables/useApiKeys'
import type {
  ChatCompletionRequest,
  ChatCompletionResponse,
  PipelineDecision,
  ApiError,
} from '~/types/api'

// ─── Non-streaming ───

export const chatService = {
  sendMessage: (body: ChatCompletionRequest): Promise<ChatCompletionResponse> =>
    api.post<ChatCompletionResponse>('/v1/chat/completions', body)
      .then((r) => r.data),
}

// ─── Provider endpoints for direct browser → API calls ───

/**
 * Base URLs for providers that support direct browser calls
 * (CORS-enabled, OpenAI-compatible streaming format).
 *
 * The Protection Compare's right panel calls these directly from the
 * browser — completely bypassing the Agent-Firewall proxy — to prove
 * the raw model accepts prompts that Agent-Firewall would block.
 */
/**
 * Build provider → base URL map from runtime env vars.
 * Override via NUXT_PUBLIC_DEEPSEEK_API_BASE.
 */
export function getProviderApiBases(): Record<string, string> {
  return {
    deepseek: (import.meta.env.NUXT_PUBLIC_DEEPSEEK_API_BASE as string) ?? 'https://api.deepseek.com',
  }
}

/** True if the provider supports direct browser → API calls. */
export function supportsDirectBrowserCall(provider: string): boolean {
  return provider in getProviderApiBases()
}

// ─── Streaming (SSE via fetch) ───

export interface StreamCallbacks {
  onToken: (token: string) => void
  onDone: () => void
  onError: (error: Error) => void
}

export interface StreamOptions {
  body: ChatCompletionRequest
  headers?: Record<string, string>
  signal?: AbortSignal
  /** Custom endpoint path (default: /v1/chat/completions) */
  url?: string
}

export async function streamChat(
  options: StreamOptions,
  callbacks: StreamCallbacks,
): Promise<Response> {
  // Browser keys are optional now. DeepSeek normally resolves server-side from
  // .env/.openclaw; localStorage remains a dev override when present.
  const model = options.body.model ?? ''
  const apiKeyHeaders: Record<string, string> = {}
  if (model) {
    const provider = detectProviderClient(model)
    const key = getKey(provider)
    if (key) {
      apiKeyHeaders['x-api-key'] = key
    }
  }

  const endpoint = options.url ?? '/v1/chat/completions'
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-client-id': 'playground',
      ...apiKeyHeaders,
      ...options.headers,
    },
    body: JSON.stringify({ ...options.body, stream: true }),
    signal: options.signal,
  })

  if (!response.ok) {
    let errorBody: unknown
    try {
      errorBody = await response.json()
    } catch {
      errorBody = {
        error: {
          message: `Server error (${response.status} ${response.statusText})`,
          type: 'server_error',
          code: String(response.status),
        },
      }
    }
    throw errorBody
  }

  return consumeOpenAIStream(response, callbacks)
}

/**
 * Stream a chat completion DIRECTLY to the DeepSeek API.
 *
 * This proves the raw model accepts prompts our proxy would block.
 * This remains a legacy/dev override; the main runtime resolves DeepSeek
 * server-side from local env/OpenClaw config.
 */
export async function streamChatDirect(
  options: {
    body: ChatCompletionRequest
    signal?: AbortSignal
  },
  callbacks: StreamCallbacks,
): Promise<Response> {
  const model = options.body.model ?? ''
  const provider = detectProviderClient(model)
  const bases = getProviderApiBases()
  const base = bases[provider]
  const key = getKey(provider)

  if (!base) {
    throw {
      error: { message: `Direct browser → ${provider} not supported. Using proxy fallback.` },
    }
  }
  if (!key) {
    throw {
      error: { message: `No API key for "${provider}".` },
    }
  }

  const response = await fetch(`${base}/v1/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${key}`,
    },
    body: JSON.stringify({ ...options.body, stream: true }),
    signal: options.signal,
  })

  if (!response.ok) {
    let errorBody: unknown
    try {
      errorBody = await response.json()
    } catch {
      errorBody = {
        error: {
          message: `${provider} error (${response.status} ${response.statusText})`,
        },
      }
    }
    throw errorBody
  }

  return consumeOpenAIStream(response, callbacks)
}

// ─── Pipeline decision extraction ───

export function extractPipelineDecision(response: Response): PipelineDecision {
  return {
    decision: (response.headers.get('x-decision') ?? 'ALLOW') as PipelineDecision['decision'],
    intent: response.headers.get('x-intent') ?? 'unknown',
    riskScore: parseFloat(response.headers.get('x-risk-score') ?? '0'),
    riskFlags: {},
  }
}

export function extractBlockDecision(errorBody: ApiError): PipelineDecision {
  return {
    decision: 'BLOCK',
    intent: errorBody.intent ?? 'unknown',
    riskScore: errorBody.risk_score ?? 0,
    riskFlags: errorBody.risk_flags ?? {},
    blockedReason: errorBody.error.message,
  }
}
