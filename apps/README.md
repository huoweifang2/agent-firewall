# Apps

| App | Tech | Port | Purpose |
|-----|------|------|---------|
| `proxy-service` | Python / FastAPI / uv | 8000 | Firewall scan pipeline, audit logs, intervention approvals, Agent Control Plane, OpenClaw discovery, runtime specs |
| `agent` | Python / FastAPI / uv | 8002 | Protected runtime graph, message ingress adapters including Telegram Bridge, OpenClaw/MCP tool execution, trace forwarding |
| `frontend` | Nuxt 4 / Vuetify | 3000 | Operator console: Attack Playground, approvals, Bot Agents, traces, skills/hooks, runtime settings |

The removed legacy target app and Docker stack are no longer part of the default product path.

## Runtime Evidence Path

The apps cooperate through one protected chain:

```text
Telegram Bridge or another ingress adapter
  -> agent /agent/chat
  -> proxy /v1/scan
  -> agent pre-tool gate
  -> OpenClaw/MCP/Internal provider
  -> agent post-tool gate
  -> proxy trace/intervention/audit records
```

The Telegram Bridge has been validated with real OpenClaw tool execution, high-sensitivity `tool_confirmation` replay, post-tool redaction, and rejected `input_block` behavior. The Bridge uses the Control Plane agent UUID for runtime-spec lookup and the OpenClaw runtime id only inside provider execution.
