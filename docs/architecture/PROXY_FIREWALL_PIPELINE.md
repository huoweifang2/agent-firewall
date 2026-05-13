# Proxy Firewall Pipeline

The proxy service exposes `POST /v1/scan` for scan-only enforcement. It does not call the LLM; it returns a deterministic firewall decision for the agent runtime.

## Scan Flow

1. Parse OpenAI-compatible messages.
2. Extract the latest user message.
3. Build shared scan context for policy metadata and request-local denylist hits.
4. Classify intent and attack category.
5. Apply policy rules and scanners.
6. Aggregate risk.
7. Return `ALLOW`, `MODIFY`, or `BLOCK`.
8. Write an audit row to `requests`.

The intent and rules nodes share the same request-local `denylist_hits` value in
`PipelineState`, so one request does not repeat denylist loading or regex matching
inside the scan pipeline.

## Intervention API

The proxy owns `/v1/interventions`:

- `POST /v1/interventions`: create a pending approval item.
- `GET /v1/interventions?status=pending`: list pending operator work.
- `GET /v1/interventions/{id}`: read one item.
- `PATCH /v1/interventions/{id}`: set `approved`, `rejected`, `completed`, or `failed`.

The agent uses this API to pause protected-runtime requests and to continue approved replays through the originating ingress adapter.

## Telegram Bridge Evidence

Telegram is one ingress adapter that consumes allowlisted bot updates and maps them to protected runtime sessions. During local validation, the proxy recorded:

- `input_scan` decisions for Telegram-originated messages.
- `tool_confirmation` interventions for high-sensitivity tools.
- `input_block` interventions for suspicious tool-forcing or bypass prompts.
- completed intervention state after approval replay.

The proxy stores the state transition and trace id, while the originating Bridge sends the user-visible pause, approval result, or blocked response back through Telegram.
