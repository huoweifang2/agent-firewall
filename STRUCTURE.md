# Agent-Firewall Structure

## Project Shape

Agent-Firewall is a local monorepo for an OpenClaw safety shell. It wraps OpenClaw/MCP tool execution with scan-only proxy checks, runtime gates, approvals, and traces.

- `apps/proxy-service`: FastAPI firewall, scan pipeline, audit log, intervention queue, Agent Control Plane, OpenClaw discovery, runtime specs.
- `apps/agent`: FastAPI protected runtime, message ingress adapters including Telegram Bridge, OpenClaw/MCP providers, traces.
- `apps/frontend`: Nuxt/Vuetify operator console at `localhost:3000`.
- `docs/architecture`: current architecture docs.
- `article`: thesis/article material, kept separate from product runtime.

## Runtime Flow

```text
Message ingress adapter -> apps/agent protected runtime
                        -> apps/proxy-service /v1/scan
                        -> runtime gates -> OpenClaw/MCP provider
                        -> post-tool gate -> trace/audit -> reply channel
```

Blocked input and confirmation-gated tools create `interventions` rows in the proxy database. The frontend approves or rejects them; the originating worker continues approved items.

Telegram Bridge has been verified as one real ingress adapter for tool workflows:

- `ALLOW` requests can execute `provider_type=openclaw` tools and return through Telegram.
- `tool_confirmation` requests pause, create an intervention, replay with `approved_intervention_id`, then complete.
- `input_block` requests remain non-executed when rejected.
- post-tool `REDACT` decisions clean tool output before trace preview and final reply.

## Local Runtime

- Python dependency manager: `uv`.
- Frontend dependency manager: npm.
- Default DB: SQLite at `~/.openclaw/agent-firewall.sqlite`.
- Default cache: in-process memory.
- Docker/infra services are no longer part of the default repository runtime.

## Important Files

- `start-local.sh`: starts proxy, agent, and frontend.
- `apps/proxy-service/src/proxy_service/interfaces/http/routers/scan.py`: scan-only firewall endpoint.
- `apps/proxy-service/src/proxy_service/interfaces/http/routers/interventions.py`: approval queue API.
- `apps/proxy-service/src/proxy_service/infrastructure/persistence/control_plane_seed.py`: seeds the protected Telegram OpenClaw gateway agent.
- `apps/proxy-service/src/proxy_service/application/control_plane/runtime_spec.py`: builds runtime specs and normalizes legacy skill metadata shapes.
- `apps/agent/src/agent_runtime/application/runtime/graph.py`: runtime graph runner.
- `apps/agent/src/agent_runtime/infrastructure/telegram_bridge.py`: optional Telegram ingress adapter and approval continuation.
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
