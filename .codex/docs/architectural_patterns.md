# Architectural Patterns

This file records patterns that recur across multiple parts of the repo. If a rule appears in one file only, it does not belong here.

## 1. Graphs + Typed State Drive Multi-Step Logic

- Both backend runtimes model orchestration as graphs over shared typed state dictionaries instead of passing opaque mutable objects between steps.
- Proxy references: `apps/proxy-service/src/proxy_service/domain/firewall/pipeline/state.py` and `apps/proxy-service/src/proxy_service/domain/firewall/pipeline/graph.py`.
- Agent references: `apps/agent/src/agent_runtime/domain/state.py` and `apps/agent/src/agent_runtime/application/runtime/graph.py`.
- Practical implication: if behavior spans more than one stage, add explicit state fields and graph edges rather than hiding flow in helper side effects.

## 2. Thin App Entrypoints, Feature Logic Below Routers

- The two FastAPI apps keep bootstrap code focused on lifecycle, middleware, and router registration.
- Proxy bootstrap references: `apps/proxy-service/src/proxy_service/bootstrap/main.py`, `apps/proxy-service/src/proxy_service/bootstrap/app.py`, and `apps/proxy-service/src/proxy_service/bootstrap/routers.py`.
- Agent bootstrap reference: `apps/agent/src/agent_runtime/bootstrap/main.py`.
- Request-specific behavior lives in routers and deeper modules instead of in app bootstrap files.
- Router references: `apps/proxy-service/src/proxy_service/interfaces/http/routers/` and `apps/agent/src/agent_runtime/interfaces/http/routers/`.
- Practical implication: add new HTTP features under `interfaces/http/routers/` plus supporting application/domain modules; avoid growing bootstrap files into feature files.

## 3. Schema-First Boundaries for Transport and Persistence

- HTTP contracts are expressed with Pydantic models, while persistence uses ORM models; routers translate between them.
- Proxy transport references: `apps/proxy-service/src/proxy_service/interfaces/http/schemas/` and `apps/proxy-service/src/proxy_service/interfaces/http/routers/`.
- Proxy persistence references: `apps/proxy-service/src/proxy_service/domain/control_plane/models.py` and `apps/proxy-service/src/proxy_service/infrastructure/persistence/session.py`.
- Agent transport references: `apps/agent/src/agent_runtime/interfaces/http/schemas.py` and `apps/agent/src/agent_runtime/interfaces/http/routers/`.
- Practical implication: when adding or changing an API field, check whether the change belongs in request/response schemas, ORM models, or both.

## 4. Deterministic Security Gates Surround Model and Tool Execution

- The repo keeps security decisions outside the model's discretion.
- Proxy request path references: `apps/proxy-service/src/proxy_service/domain/firewall/pipeline/graph.py`, `apps/proxy-service/src/proxy_service/interfaces/http/routers/scan.py`, and `apps/proxy-service/src/proxy_service/application/firewall/runner.py`.
- Proxy scan context is carried in `PipelineState`; denylist hits are cached as `denylist_hits` so intent and rules nodes do not duplicate the same request scan.
- Agent tool path references: `apps/agent/src/agent_runtime/application/runtime/nodes/pre_tool_gate.py`, `apps/agent/src/agent_runtime/application/runtime/nodes/post_tool_gate.py`, and `apps/agent/src/agent_runtime/application/runtime/tool_protection.py`.
- Pattern catalogs live outside orchestration nodes: `intent_patterns.py` for proxy intent strings and `gate_patterns.py` for agent gate regexes.
- Practical implication: new capabilities should enter through an explicit gate or scanner step, not as inline checks buried in LLM prompts.

## 5. Shared Resources Are Process-Level Singletons or Lazy Factories

- Expensive or shared runtime resources are initialized once and then reused.
- Settings references: `apps/proxy-service/src/proxy_service/infrastructure/config.py` and `apps/agent/src/agent_runtime/infrastructure/config.py`.
- Shared DB reference: `apps/proxy-service/src/proxy_service/infrastructure/persistence/session.py`.
- Compiled graph references: `apps/proxy-service/src/proxy_service/domain/firewall/pipeline/graph.py` and `apps/agent/src/agent_runtime/application/runtime/graph.py`.
- Shared service references: `apps/agent/src/agent_runtime/domain/rbac/service.py`, `apps/agent/src/agent_runtime/domain/limits/service.py`, and `apps/agent/src/agent_runtime/domain/trace/store.py`.
- Practical implication: prefer extending an existing cached service or singleton accessor before introducing per-request construction for heavyweight resources.

## 6. Frontend Flow Is Service -> Composable -> Page/Component

- The frontend separates raw HTTP access, state/query logic, and presentation.
- Shared HTTP and SSE helpers live in `apps/frontend/app/services/http.ts` and `apps/frontend/app/services/sse.ts`.
- Service references: `apps/frontend/app/services/api.ts`, `apps/frontend/app/services/agentService.ts`, and `apps/frontend/app/services/chatService.ts`.
- Query/composable references: `apps/frontend/app/composables/`.
- Page/component references: `apps/frontend/app/pages/` and `apps/frontend/app/components/`.
- Practical implication: when adding UI features, put transport concerns in `app/services/`, server-state behavior in `app/composables/`, and keep pages/components focused on rendering and interaction.

## 7. Auditability Is a First-Class Concern

- Both the proxy and the agent produce structured traces rather than relying on logs alone.
- Proxy request logging references: `apps/proxy-service/src/proxy_service/application/services/request_logger.py` and `apps/proxy-service/src/proxy_service/domain/firewall/pipeline/nodes/logging_node.py`.
- Agent trace references: `apps/agent/src/agent_runtime/domain/trace/accumulator.py`, `apps/agent/src/agent_runtime/domain/trace/store.py`, and gate/tool nodes under `apps/agent/src/agent_runtime/application/runtime/nodes/`.
- Practical implication: when changing control flow, preserve trace fields and audit writes so blocked or modified decisions remain explainable.
