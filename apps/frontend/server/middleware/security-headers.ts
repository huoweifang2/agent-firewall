export default defineEventHandler((event) => {
  const config = useRuntimeConfig()

  const apiBase: string = (config.public.apiBase as string) || 'http://localhost:8000'
  const agentBase: string = (config.public.agentApiBase as string) || 'http://localhost:8002'

  // DeepSeek direct API is kept only for Compare's legacy/dev bypass panel.
  const providerApis = 'https://api.deepseek.com'

  // Dev mode: allow HMR WebSocket
  const isDev = import.meta.dev
  const devSources = isDev ? ' ws://localhost:3000 ws://localhost:24678' : ''

  const connectSrc = `'self' ${apiBase} ${agentBase} ${providerApis}${devSources}`

  const csp = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
    "font-src 'self' data:",
    "img-src 'self' data: blob:",
    `connect-src ${connectSrc}`,
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join('; ')

  setHeaders(event, {
    'Content-Security-Policy': csp,
    'X-Frame-Options': 'DENY',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=()',
    'X-XSS-Protection': '0',
  })
})
