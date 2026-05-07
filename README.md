# Agent-Firewall

Agent-Firewall is a local safety shell around an OpenClaw runtime. It sits between message ingress adapters and OpenClaw/MCP/Internal tools, enforcing input scanning, runtime tool gates, human approvals, and trace/audit evidence before capabilities are allowed to run.

Telegram is the currently implemented message ingress adapter. It is useful for real-world chat traffic, but it is not the core product boundary. The core boundary is the Agent-Firewall layer that wraps OpenClaw execution.

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

## Local Setup

Requirements:

- `uv`
- Node.js and npm
- OpenClaw CLI configured on this machine
- Telegram bot tokens in `~/.openclaw/openclaw.json` only if the Telegram Bridge adapter is enabled

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

- Do not commit real API keys, Telegram bot tokens, gateway tokens, or local `.env` files.
- `/agent/openclaw/direct` exists only for Compare. It intentionally bypasses Agent-Firewall and must not be used for protected runtime traffic.
- Normal OpenClaw skill execution, MCP calls, and message-adapter tool use should flow through the Agent-Firewall runtime graph and gates.
