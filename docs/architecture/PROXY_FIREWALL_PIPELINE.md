# Proxy Firewall Pipeline

The proxy service exposes `POST /v1/scan` for scan-only enforcement. It does not call the LLM; it returns a deterministic firewall decision for the agent runtime.

## Scan Flow

1. Parse OpenAI-compatible messages.
2. Extract the latest user message.
3. Classify intent and attack category.
4. Apply policy rules and scanners.
5. Aggregate risk.
6. Return `ALLOW`, `MODIFY`, or `BLOCK`.
7. Write an audit row to `requests`.

## Intervention API

The proxy owns `/v1/interventions`:

- `POST /v1/interventions`: create a pending approval item.
- `GET /v1/interventions?status=pending`: list pending operator work.
- `GET /v1/interventions/{id}`: read one item.
- `PATCH /v1/interventions/{id}`: set `approved`, `rejected`, `completed`, or `failed`.

The agent uses this API to pause protected-runtime requests and to continue approved replays through the originating ingress adapter.
