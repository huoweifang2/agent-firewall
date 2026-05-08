# Agent-Firewall

Agent-Firewall is a local safety shell around an OpenClaw runtime. It sits between message ingress adapters and OpenClaw/MCP/Internal tools, enforcing input scanning, runtime tool gates, human approvals, and trace/audit evidence before capabilities are allowed to run.

Telegram is the currently implemented message ingress adapter. It is useful for real-world chat traffic, but it is not the core product boundary. The core boundary is the Agent-Firewall layer that wraps OpenClaw execution.

The Agent Control Plane in `apps/proxy-service` stores protected bot-agent registrations, role/tool/skill bindings, runtime specs, rollout state, and trace metadata. Public HTTP routes remain `/v1/agents`, `/v1/openclaw/*`, and `/v1/interventions`.

## Protected Runtime Path

```text
Message ingress adapter
  -> apps/agent protected runtime
  -> apps/proxy-service /v1/scan
  -> Agent runtime gates
  -> OpenClaw skill / MCP provider
  -> post-tool gate
  -> trace + audit log
  -> reply channel
```

If Agent-Firewall blocks an input or a sensitive tool needs approval, the request is paused and an item appears in `localhost:3000` under **Approvals / Audit**. Approving it lets the protected runtime continue and send the final reply through the originating adapter.

## Verified Telegram Tool Workflow

The current local workflow has been exercised through an allowlisted Telegram bot without exposing the bot token or chat identifier. The validated path is:

```text
Telegram Bridge -> /agent/chat -> /v1/scan -> pre-tool gate
  -> OpenClaw provider -> post-tool gate -> Trace / Audit -> Telegram reply
```

Observed workflow states:

- A normal `openclaw_summarize` request passes `/v1/scan`, the pre-tool gate, OpenClaw provider execution, post-tool filtering, and final Telegram reply.
- A high-sensitivity tool creates a `tool_confirmation` intervention, pauses execution, then continues after approval by replaying with `approved_intervention_id`.
- Tool output is scanned after execution; PII/secret-like content is redacted before the final reply and trace preview.
- Suspicious input creates an `input_block` intervention. Rejected blocks are not replayed and do not execute tools.

The Telegram Bridge must be configured with the Control Plane agent UUID, not the OpenClaw runtime id such as `coder`, so runtime-spec lookup resolves the protected agent registration.

## Local Setup

Requirements:

- `uv`
- Node.js and npm
- OpenClaw CLI configured on this machine
- Telegram Bridge credentials in `~/.openclaw/openclaw.json` only if that ingress adapter is enabled

Install dependencies:

```bash
make setup
```

Configure local secrets in ignored files:

```bash
cp apps/proxy-service/.env.example apps/proxy-service/.env.local
cp apps/agent/.env.example apps/agent/.env.local
```

Start the local stack:

```bash
./start-local.sh
```

Open:

- Frontend: `http://localhost:3000`
- Proxy API: `http://localhost:8000`
- Agent API: `http://localhost:8002`

The default local database is SQLite at `~/.openclaw/agent-firewall.sqlite`; Redis, Docker, and Langfuse are not required for the default path.

## Main Surfaces

- **Attack Playground**: first page and first nav item; manual prompt attack testing.
- **Approvals / Audit**: pending interventions for blocked input and tool confirmations.
- **Bot Agents**: Agent Control Plane records for Telegram-facing main agents, subagents, tools, skills, and delegation.
- **Skills & Hooks**: discovers local OpenClaw skills/hooks and binds eligible skills as protected Agent-Firewall tools.
- **Trace / Audit**: full agent runtime traces, including tool plans, pre-tool gates, tool execution, post-tool gates, and final responses.
- **Runtime Settings**: redacted OpenClaw, DeepSeek, ingress adapter, and gateway diagnostics.

## Useful Commands

```bash
make lint
make test
make frontend-build
```

OpenClaw diagnostics:

```bash
openclaw status --json --no-usage
openclaw agents list --json
openclaw skills list --json
openclaw hooks list --json
```

## Security Notes

- Do not commit real API keys, Telegram credentials, gateway tokens, or local `.env` files.
- `/agent/openclaw/direct` exists only for Compare. It intentionally bypasses Agent-Firewall and must not be used for protected runtime traffic.
- Normal OpenClaw skill execution, MCP calls, and message-adapter tool use should flow through the Agent-Firewall runtime graph and gates.
- Legacy `AgentSkill` metadata may exist as older list/string values in local SQLite. Runtime specs normalize those shapes to dictionaries before serving the agent runtime, avoiding validation failures during Telegram Bridge requests.
