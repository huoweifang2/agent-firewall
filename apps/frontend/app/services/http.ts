import axios from 'axios'
import type { AxiosInstance, InternalAxiosRequestConfig } from 'axios'

export const API_BASE_URL = import.meta.env.NUXT_PUBLIC_API_BASE ?? 'http://localhost:8000'
export const AGENT_API_BASE_URL = import.meta.env.NUXT_PUBLIC_AGENT_API_BASE ?? 'http://localhost:8002'

function correlationId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `cid-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function createCorrelatedJsonClient(baseURL: string, timeout: number): AxiosInstance {
  const client = axios.create({
    baseURL,
    timeout,
    headers: {
      'Content-Type': 'application/json',
    },
  })

  client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    config.headers['x-correlation-id'] = correlationId()
    return config
  })

  return client
}

export function newCorrelationId(): string {
  return correlationId()
}

export function warnIfInsecureProductionBase(envName: string, baseURL: string) {
  if (import.meta.env.PROD && !baseURL.startsWith('https://')) {
    console.error(`[api] ${envName} must use https:// in production`)
  }
}
