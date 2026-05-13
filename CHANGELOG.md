# Changelog

## Current Focus

This workspace is now maintained as an OpenClaw safety-shell Agent-Firewall project.

- Primary path: message ingress adapter -> Agent-Firewall protected runtime -> proxy scan -> runtime tool gates -> OpenClaw skill/MCP provider -> reply channel.
- Telegram Bridge is the currently implemented chat ingress adapter, not the product boundary.
- Local console: `localhost:3000` opens Attack Playground, with Approvals / Audit available for paused protected-runtime requests.
- Python services are managed with `uv`; local persistence defaults to SQLite.
- OpenClaw skills and MCP tools are imported as protected providers and pass through RBAC, argument scanning, limits, confirmation, post-tool filtering, and trace recording.
- Proxy scan context now carries request-local denylist hits so intent and rules checks do not repeat the same denylist work.
- Agent pre-tool and post-tool gates share tool-protection precedence and scanner pattern catalogs.
- Frontend API access uses shared correlated HTTP clients and shared SSE parsing helpers.
- Legacy infrastructure and demo artifacts have been removed from the active product path.

## Current Local Validation

- Verified a real Telegram ingress workflow through `/agent/chat`, `/v1/scan`, pre-tool gate, OpenClaw provider execution, post-tool gate, trace persistence, and Telegram reply.
- Verified high-sensitivity `tool_confirmation` pause, approval, `approved_intervention_id` replay, and completed intervention state.
- Verified post-tool `REDACT` behavior for sensitive tool output and `input_block` behavior for suspicious input.
- Fixed runtime-spec compatibility for legacy `AgentSkill` metadata shapes by normalizing list/string values to dictionaries before serving the runtime.
- Confirmed the Telegram Bridge must reference the Control Plane agent UUID for protected runtime-spec lookup.
- Current verification commands: `make lint`, `make test`, `cd apps/frontend && npm test`, and `make frontend-build`.

Older generated release notes were intentionally replaced because they described a different product shape.
