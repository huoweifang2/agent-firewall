import type { AxiosError } from 'axios'
import { API_BASE_URL, createCorrelatedJsonClient, warnIfInsecureProductionBase } from './http'
import type { ApiError } from '~/types/api'

export interface AppError {
  message: string
  status: number | null
  code: string
  raw?: unknown
}

function mapApiError(error: AxiosError<ApiError>): AppError {
  if (!error.response) {
    return {
      message: 'Cannot reach Agent-Firewall service',
      status: null,
      code: 'NETWORK_ERROR',
    }
  }

  const { status, data } = error.response
  const serverMessage = data?.error?.message

  const map: Record<number, AppError> = {
    403: {
      message: serverMessage ?? 'Request blocked by policy',
      status: 403,
      code: 'BLOCKED',
      raw: data,
    },
    404: { message: 'Resource not found', status: 404, code: 'NOT_FOUND' },
    502: { message: 'LLM provider unavailable', status: 502, code: 'LLM_DOWN' },
    504: { message: 'LLM request timed out', status: 504, code: 'LLM_TIMEOUT' },
  }

  return map[status] ?? {
    message: serverMessage ?? `Server error (${status})`,
    status,
    code: 'SERVER_ERROR',
  }
}

// Block insecure API base in production — auth tokens must not travel over plain HTTP.
warnIfInsecureProductionBase('NUXT_PUBLIC_API_BASE', API_BASE_URL)

const api = createCorrelatedJsonClient(API_BASE_URL, 30_000)

// Response interceptor — map errors
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    const mapped = mapApiError(error)
    return Promise.reject(mapped)
  },
)

export { api }
