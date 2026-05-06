# Agent-Firewall

Agent-Firewall is now a Telegram-first security gateway for a personal OpenClaw bot. Telegram is the user entry point; the local web app at `http://localhost:3000` is the operator console for attack testing, approvals, traces, and OpenClaw skill/MCP binding.

## Runtime Path

```text
Telegram Bot
  -> apps/agent Telegram Bridge
  -> apps/proxy-service /v1/scan
  -> apps/agent runtime graph
  -> pre-tool gate
  -> OpenClaw skill / MCP provider
  -> post-tool gate
  -> trace + audit log
  -> Telegram reply
```

If Agent-Firewall blocks an input or a sensitive tool needs approval, Telegram receives a pause message and the item appears in `localhost:3000` under **Approvals / Audit**. Approving it lets the agent continue and send the final reply back to Telegram.

## Local Setup

Requirements:

- `uv`
- Node.js and npm
- OpenClaw CLI configured on this machine
- Telegram bot tokens already present in `~/.openclaw/openclaw.json`

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
- **Approvals / Audit**: pending Telegram interventions for blocked input and tool confirmations.
- **Skills & Hooks**: discovers local OpenClaw skills/hooks and binds eligible skills as protected Agent-Firewall tools.
- **Trace / Audit**: full agent runtime traces, including tool plans, pre-tool gates, tool execution, post-tool gates, and final responses.
- **Runtime Settings**: redacted OpenClaw, DeepSeek, Telegram Bridge, and gateway diagnostics.

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

- Do not commit real API keys, Telegram bot tokens, gateway tokens, or local `.env` files.
- `/agent/openclaw/direct` exists only for Compare. It intentionally bypasses Agent-Firewall and must not be used as the Telegram path.
- All normal Telegram tool use, OpenClaw skill execution, and MCP calls should flow through the runtime graph and gates.
