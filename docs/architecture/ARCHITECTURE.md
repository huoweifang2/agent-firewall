# Architecture

Agent-Firewall is a local safety shell around an OpenClaw runtime. It places deterministic scan, gate, approval, and audit controls between message ingress adapters and OpenClaw/MCP/Internal tool execution.

## Components

- **Message ingress adapters (`apps/agent`)**: send external messages into the protected runtime. Telegram Bridge is the currently implemented chat adapter.
- **Proxy Service (`apps/proxy-service`)**: owns `/v1/scan`, request audit logs, `/v1/interventions`, and the Agent Control Plane for bot-agent registrations, OpenClaw discovery, runtime specs, roles, tools, skills, rollout, and trace metadata.
- **Agent Runtime (`apps/agent`)**: executes the runtime graph, applies pre-tool and post-tool gates, calls OpenClaw skills/MCP providers, and forwards traces.
- **Frontend (`apps/frontend`)**: operator console for Attack Playground, Approvals / Audit, Bot Agents, Skills & Hooks, Trace / Audit, and Runtime Settings.

## Main Flow

```text
Message ingress adapter
  -> /agent/chat
  -> /v1/scan
  -> LLM tool planning
  -> pre-tool gate
  -> OpenClaw skill / MCP provider
  -> post-tool gate
  -> final response
  -> audit + trace
  -> reply channel
```

The Telegram Bridge is the currently verified ingress adapter for this flow. A real local run exercised a safe OpenClaw skill request, a high-sensitivity confirmation request, post-tool redaction, and an input block. The trace evidence for those flows is stored under the Control Plane agent trace APIs; public documentation should describe only decisions and state transitions, not raw Telegram tokens, chat identifiers, or API keys.

## Human Intervention

The runtime pauses when:

- `/v1/scan` returns `BLOCK`.
- A tool call is blocked by pre-tool checks.
- A tool requires confirmation.

The runtime creates an intervention row. The frontend approves or rejects it. Approved interventions are picked up by the originating worker and replayed with `approved_intervention_id`.

For Telegram, the Bridge creates `input_block`, `tool_block`, or `tool_confirmation` interventions and then polls approved Telegram interventions. Replays call `/agent/chat` with the original message plus `approved_intervention_id`; the runtime verifies that intervention before allowing confirmation-gated tools.

## Runtime Spec Compatibility

The Telegram Bridge must pass the Agent Control Plane agent UUID when calling the protected runtime. OpenClaw runtime ids such as `coder` are used by the provider layer, but they are not valid Control Plane ids for `/runtime-spec`.

Runtime specs also normalize legacy `AgentSkill` metadata. Older local SQLite rows may store `constraints` as a list or `output_contract` as a string; the runtime-spec builder converts those values into dictionaries before serving the agent runtime.

## Local Persistence

Default local persistence is SQLite:

```text
~/.openclaw/agent-firewall.sqlite
```

The default cache is in-process memory. Docker, Redis, Postgres, and Langfuse are not required for the current local path.
