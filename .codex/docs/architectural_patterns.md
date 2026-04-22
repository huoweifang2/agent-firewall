# Architectural Patterns

This file records only patterns that recur across multiple parts of the repo. If a rule appears in one file only, it does not belong here.

## 1. LangGraph + Typed State Drives Multi-Step Logic

- Both backend runtimes model orchestration as LangGraph graphs over shared typed state dictionaries instead of passing opaque mutable objects between steps.
- Proxy references: `apps/proxy-service/src/pipeline/state.py:1-56` and `apps/proxy-service/src/pipeline/graph.py:1-86`.
- Agent references: `apps/agent-demo/src/agent/state.py:1-104` and `apps/agent-demo/src/agent/graph.py:1-151`.
- Practical implication: if behavior spans more than one stage, add explicit state fields and graph edges rather than hiding flow in helper side effects.

## 2. Thin App Entrypoints, Feature Logic Below Routers

- The two FastAPI apps keep `main.py` focused on lifecycle, middleware, and router registration.
- Proxy bootstrap references: `apps/proxy-service/src/main.py:33-206`.
- Agent bootstrap references: `apps/agent-demo/src/main.py:103-147`.
- Request-specific behavior lives in routers and deeper modules instead of in the app bootstrap.
- Router references: `apps/proxy-service/src/routers/chat.py:93-218`, `apps/proxy-service/src/routers/scan.py:31-109`, `apps/proxy-service/src/routers/policies.py:54-152`, `apps/agent-demo/src/routers/chat.py:26-117`.
- Practical implication: add new HTTP features under `src/routers/` plus supporting modules; avoid growing `main.py` into a feature file.

## 3. Schema-First Boundaries for Transport and Persistence

- HTTP contracts are expressed with Pydantic models, while persistence uses ORM models; routers translate between them.
- Proxy transport references: `apps/proxy-service/src/schemas/policy.py:1-41`, `apps/proxy-service/src/schemas/request.py:1-95`, `apps/proxy-service/src/routers/policies.py:15-16`, `apps/proxy-service/src/routers/requests.py:14-17`.
- Proxy persistence references: `apps/proxy-service/src/models/policy.py:1-32` and `apps/proxy-service/src/models/request.py:1-50`.
- Agent transport references: `apps/agent-demo/src/schemas.py:1-56` and `apps/agent-demo/src/routers/chat.py:14-20`.
- Practical implication: when adding or changing an API field, check whether the change belongs in request/response schemas, ORM models, or both.

## 4. Deterministic Security Gates Surround Model and Tool Execution

- The repo consistently keeps security decisions outside the model’s discretion.
- Proxy request path references: `apps/proxy-service/src/pipeline/graph.py:29-86`, `apps/proxy-service/src/routers/chat.py:129-205`, `apps/proxy-service/src/routers/scan.py:1-109`.
- Agent tool path references: `apps/agent-demo/src/agent/nodes/pre_tool_gate.py:1-280`, `apps/agent-demo/src/agent/nodes/post_tool_gate.py:1-257`, `apps/agent-demo/src/agent/graph.py:42-136`.
- Practical implication: new capabilities should usually enter through an explicit gate or scanner step, not as inline checks buried in LLM prompts.

## 5. Shared Resources Are Process-Level Singletons or Lazy Factories

- Expensive or shared runtime resources are initialized once and then reused.
- Cached settings references: `apps/proxy-service/src/config.py:51-129`, `apps/agent-demo/src/config.py:8-42`.
- Shared DB/Redis references: `apps/proxy-service/src/db/session.py:10-50`.
- Compiled graph references: `apps/proxy-service/src/pipeline/graph.py:85-86` and `apps/agent-demo/src/agent/graph.py:141-151`.
- Shared service references: `apps/agent-demo/src/agent/rbac/service.py:30-32`, `apps/agent-demo/src/agent/rbac/service.py:207-218`.
- Practical implication: prefer extending an existing cached service or singleton accessor before introducing per-request construction for heavyweight resources.

## 6. Frontend Flow Is Service -> Composable -> Page/Component

- The frontend repeatedly separates raw HTTP access, state/query logic, and presentation.
- Shared HTTP client references: `apps/frontend/app/services/api.ts:1-73`, `apps/frontend/app/services/agentService.ts:1-121`.
- Query/composable references: `apps/frontend/app/composables/usePolicies.ts:1-43`, `apps/frontend/app/composables/useAgents.ts:11-89`.
- Page usage references: `apps/frontend/app/pages/policies.vue:173-260`, `apps/frontend/app/pages/agents/index.vue:165-220`.
- Practical implication: when adding UI features, put transport concerns in `app/services/`, server-state behavior in `app/composables/`, and keep pages/components focused on rendering and interaction.

## 7. Auditability Is a First-Class Concern

- Both the proxy and the agent produce structured traces rather than relying on logs alone.
- Proxy request logging references: `apps/proxy-service/src/services/request_logger.py:76-173`, `apps/proxy-service/src/routers/chat.py:143-151`, `apps/proxy-service/src/routers/scan.py:74-79`.
- Agent trace references: `apps/agent-demo/src/agent/state.py:103-104`, `apps/agent-demo/src/agent/nodes/pre_tool_gate.py:25`, `apps/agent-demo/src/agent/nodes/post_tool_gate.py:23`, `apps/agent-demo/src/routers/chat.py:73-115`.
- Practical implication: when changing control flow, preserve trace fields and audit writes so blocked or modified decisions remain explainable.
