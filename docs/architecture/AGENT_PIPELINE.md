# Agent Runtime Pipeline

`apps/agent/src/agent_runtime/application/runtime/graph.py` runs the protected runtime graph.

## Steps

1. **Input**: load session history, sanitize user input, load runtime spec, initialize trace.
2. **Intent**: classify the user message for trace and policy context.
3. **Policy**: resolve allowed tools for the effective role.
4. **LLM call**: scan the user message through Proxy `/v1/scan`, then ask the model to answer or propose tool calls.
5. **Pre-tool gate**: enforce RBAC, schema validation, injection checks, budgets, and confirmation.
6. **Tool execution**: dispatch to internal, OpenClaw, or MCP providers.
7. **Post-tool gate**: redact PII/secrets and block tool-result injection.
8. **Response**: build the final user-visible message.
9. **Memory/trace**: store conversation memory and persist the structured trace.

## Provider Rules

- `provider_type=openclaw`: executes the named OpenClaw skill through the scoped OpenClaw provider.
- `provider_type=mcp`: executes the declarative MCP provider endpoint.
- `provider_type=internal`: limited local helper tools and subagent orchestration.

All provider calls flow through pre-tool and post-tool gates unless the runtime spec explicitly disables a gate for that tool. The shared tool-protection helper applies the current priority order: runtime-spec `pre_gate_enabled` / `post_gate_enabled` flags first, legacy middleware protection metadata second, and unknown tools default to protected.

Pre-tool and post-tool nodes share gate regex catalogs through `agent_runtime/domain/security/gate_patterns.py`; the nodes themselves keep the orchestration and decision logic.

The local Telegram tool validation used `provider_type=openclaw` with the `openclaw_summarize` protected tool. Trace records should show pre-tool decisions, tool execution metadata, post-tool decisions, and the final response; raw tokens and chat identifiers must not be copied into documentation or UI previews.

## Approved Replays

Approved interventions call `/agent/chat` with `approved_intervention_id`. The runtime verifies the intervention with the proxy before treating the input scan/confirmation as approved. Telegram Bridge is one ingress adapter that can perform this replay, but the runtime contract is adapter-neutral.

High-sensitivity tools are expected to follow this state sequence:

```text
LLM proposes tool -> pre-tool gate REQUIRE_CONFIRMATION
  -> intervention kind=tool_confirmation status=pending
  -> operator approves
  -> replay with approved_intervention_id
  -> pre-tool gate ALLOW
  -> provider execution
  -> post-tool gate
  -> intervention status=completed
```

Rejected `input_block` interventions do not replay and therefore do not execute provider tools.
