# Agent-Firewall Structure

## Project Shape

Agent-Firewall is a local monorepo for a Telegram-first OpenClaw bot firewall.

- `apps/proxy-service`: FastAPI firewall, scan pipeline, audit log, intervention queue, OpenClaw discovery, runtime specs.
- `apps/agent`: FastAPI agent runtime, Telegram Bridge, protected runtime graph, OpenClaw/MCP providers, traces.
- `apps/frontend`: Nuxt/Vuetify operator console at `localhost:3000`.
- `docs/architecture`: current architecture docs.
- `docs/archive`: historical design notes only.
- `artical`: thesis/article material, kept separate from product runtime.

## Runtime Flow

```text
Telegram -> apps/agent -> apps/proxy-service /v1/scan
         -> apps/agent runtime graph
         -> pre-tool gate -> OpenClaw/MCP provider -> post-tool gate
         -> trace/audit -> Telegram
```

Blocked input and confirmation-gated tools create `interventions` rows in the proxy database. The frontend approves or rejects them; the Telegram Bridge worker continues approved items.

## Local Runtime

- Python dependency manager: `uv`.
- Frontend dependency manager: npm.
- Default DB: SQLite at `~/.openclaw/agent-firewall.sqlite`.
- Default cache: in-process memory.
- Docker/infra services are no longer part of the default repository runtime.

## Important Files

- `start-local.sh`: starts proxy, agent, and frontend.
- `apps/proxy-service/src/routers/scan.py`: scan-only firewall endpoint.
- `apps/proxy-service/src/routers/interventions.py`: approval queue API.
- `apps/proxy-service/src/wizard/seed.py`: seeds `Telegram OpenClaw Gateway`.
- `apps/agent/src/agent/graph.py`: runtime graph runner.
- `apps/agent/src/agent/telegram_bridge.py`: Telegram polling and approval continuation.
- `apps/frontend/app/pages/approvals.vue`: operator approval page.
- `apps/frontend/app/components/app-nav-drawer.vue`: navigation order.

## Commands

```bash
make setup
./start-local.sh
make lint
make test
make frontend-build
```
