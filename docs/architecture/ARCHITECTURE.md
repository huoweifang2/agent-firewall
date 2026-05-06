# Architecture

Agent-Firewall is a local Telegram-first firewall for a personal OpenClaw bot.

## Components

- **Telegram Bridge (`apps/agent`)**: polls the configured OpenClaw Telegram bot account, sends messages into the protected runtime, and sends replies back to Telegram.
- **Proxy Service (`apps/proxy-service`)**: owns `/v1/scan`, request audit logs, OpenClaw discovery, runtime specs, and `/v1/interventions`.
- **Agent Runtime (`apps/agent`)**: executes the runtime graph, applies pre-tool and post-tool gates, calls OpenClaw skills/MCP providers, and forwards traces.
- **Frontend (`apps/frontend`)**: operator console for Attack Playground, Approvals / Audit, Skills & Hooks, Trace / Audit, and Runtime Settings.

## Main Flow

```text
Telegram message
  -> Telegram Bridge
  -> /agent/chat
  -> /v1/scan
  -> LLM tool planning
  -> pre-tool gate
  -> OpenClaw skill / MCP provider
  -> post-tool gate
  -> final response
  -> audit + trace
  -> Telegram reply
```

## Human Intervention

The runtime pauses when:

- `/v1/scan` returns `BLOCK`.
- A tool call is blocked by pre-tool checks.
- A tool requires confirmation.

The bridge creates an intervention row. The frontend approves or rejects it. Approved Telegram interventions are picked up by the bridge worker and replayed with `approved_intervention_id`.

## Local Persistence

Default local persistence is SQLite:

```text
~/.openclaw/agent-firewall.sqlite
```

The default cache is in-process memory. Docker, Redis, Postgres, and Langfuse are not required for the current local path.
