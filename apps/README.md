# Apps

| App | Tech | Port | Purpose |
|-----|------|------|---------|
| `proxy-service` | Python / FastAPI / uv | 8000 | Firewall scan pipeline, audit logs, intervention approvals, Agent Control Plane, OpenClaw discovery, runtime specs |
| `agent` | Python / FastAPI / uv | 8002 | Protected runtime graph, message ingress adapters including Telegram Bridge, OpenClaw/MCP tool execution, trace forwarding |
| `frontend` | Nuxt 4 / Vuetify | 3000 | Operator console: Attack Playground, approvals, Bot Agents, traces, skills/hooks, runtime settings |

The removed legacy target app and Docker stack are no longer part of the default product path.
