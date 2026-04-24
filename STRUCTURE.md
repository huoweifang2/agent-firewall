# Agent-Firewall Structure

## Project Overview

- Purpose: Agent-Firewall is a security-focused monorepo for tool-calling AI systems. The core idea is deterministic enforcement around LLM traffic and tool usage, not LLM-as-judge. See `README.md:1-69` and `docs/architecture/ARCHITECTURE.md:8-139`.
- System shape: the main product path is `frontend -> proxy-service -> LLM provider`, with `agent` showing in-agent guardrails and `reference-chat-target` acting as a benchmark target rather than a product service. See `apps/README.md:1-9`, `infra/docker-compose.yml:66-150`.
- Default mental model: treat the repo as three actively developed apps plus shared infra and docs, not as a single deployable binary. See `Makefile:16-63` and `infra/docker-compose.yml:7-157`.

## Tech Stack

- Backend runtime: Python 3.12 with FastAPI, Pydantic Settings, LangGraph, LiteLLM, structlog, SQLAlchemy async, Alembic, asyncpg, and Redis. See `apps/proxy-service/pyproject.toml:1-35` and `apps/agent/pyproject.toml:1-27`.
- Frontend runtime: Nuxt 4 SPA with Vue 3, Vuetify, Pinia, Vue Query, Axios, and Zod. See `apps/frontend/package.json:1-41` and `apps/frontend/nuxt.config.ts:2-73`.
- Local infrastructure: Docker Compose brings up Postgres, Redis, Langfuse, and optional containerized app services. See `infra/docker-compose.yml:7-157`.
- Persistence and observability: Postgres is the main durable store, Redis is the shared ephemeral/cache layer, and Langfuse is the optional tracing surface. See `docs/architecture/ARCHITECTURE.md:134-188`, `apps/proxy-service/src/db/session.py:1-50`, `apps/proxy-service/src/main.py:56-135`.

## Key Directories

- `apps/proxy-service/`: the OpenAI-compatible firewall API. `src/main.py` is bootstrap and router wiring, `src/pipeline/` contains the LangGraph firewall, `src/routers/` exposes product APIs, `src/red_team/` contains attack-runner code, and `src/wizard/` holds the agent setup flows. Start with `apps/proxy-service/src/main.py:33-206`, `apps/proxy-service/src/pipeline/graph.py:1-86`, `apps/proxy-service/src/pipeline/state.py:1-56`, and `apps/proxy-service/src/routers/scan.py:1-109`.
- `apps/agent/`: the customer-support agent runtime that scans input through the proxy and then applies its own tool guardrails. The important surfaces are `src/main.py`, `src/agent/graph.py`, `src/agent/nodes/`, `src/agent/rbac/`, and `src/agent/tools/`. Start with `apps/agent/src/main.py:37-147`, `apps/agent/src/agent/graph.py:1-151`, `apps/agent/src/agent/state.py:1-104`, `apps/agent/src/agent/nodes/pre_tool_gate.py:1-280`, and `apps/agent/src/agent/nodes/post_tool_gate.py:1-257`.
- `apps/frontend/`: the operator dashboard SPA. `app/pages/` defines routes, `app/components/` holds feature UI, `app/composables/` owns query/mutation logic, and `app/services/` centralizes HTTP clients. Start with `apps/frontend/nuxt.config.ts:6-72`, `apps/frontend/app/layouts/default.vue:1-38`, `apps/frontend/app/services/api.ts:1-73`, `apps/frontend/app/composables/usePolicies.ts:1-43`, and `apps/frontend/app/pages/policies.vue:173-260`.
- `apps/reference-chat-target/`: a realistic but intentionally simple target service used for benchmarking protected vs raw model behavior. It is useful when working on red-team or end-to-end validation flows, but not the default place to start for product changes. See `apps/reference-chat-target/README.md:1-174`.
- `infra/`: shared local infrastructure definitions and verification scripts. Use this when ports, containers, env wiring, or boot order matter. See `infra/docker-compose.yml:1-157` and `infra/scripts/verify-stack.sh:1`.
- `docs/architecture/`: current high-level human docs for architecture, threat model, and system pipelines. Prefer this directory before reading historical specs such as `docs/archive/agents-implementation/README.md:1` or `docs/archive/ROADMAP.spec.md:1`. Start with `docs/architecture/ARCHITECTURE.md:1-228`.
- `scripts/`: repo-level helpers such as demo seeding and pentest utilities. See `Makefile:57-59`.

## Essential Build/Test Commands

- Install repo dependencies for the actively developed apps: `make setup` (`Makefile:50-55`).
- Start only shared infra, then run apps locally in separate terminals: `make dev` (`Makefile:32-38`).
- Start infra plus all three local apps together: `make dev-all` (`Makefile:40-48`).
- Start the full Dockerized stack: `make up`; stop it with `make down` (`Makefile:16-30`, `Makefile:61-63`).
- Lint the repo: `make lint` (`Makefile:75-79`).
- Run the main Python test suites: `make test` (`Makefile:99-102`).
- Run the deterministic attack-scenario suite for the proxy: `make test-scenarios` (`Makefile:107-108`).
- Verify local stack health: `make verify` (`Makefile:133-135`).

## Additional Documentation

- Check `.codex/docs/architectural_patterns.md:1` when the task touches multiple modules and you need the recurring conventions rather than a single feature implementation.
- Check `.codex/docs/source_docs.md:1` when you need the best next human-written doc for a subsystem before diving into implementation files.
