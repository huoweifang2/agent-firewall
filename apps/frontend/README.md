# Agent-Firewall Frontend

Nuxt/Vuetify console for the OpenClaw safety-shell Agent-Firewall workflow.

`http://localhost:3000` opens Attack Playground. The main navigation then
exposes Approvals / Audit, OpenClaw Sandbox, OpenClaw Agents, Skills & Hooks,
and Trace / Audit.

Approvals / Audit is part of the protected runtime path, not just a UI demo.
Blocked Telegram input creates `input_block` rows, and high-sensitivity tools
create `tool_confirmation` rows. Approved Telegram interventions are replayed by
the originating Bridge with `approved_intervention_id`; rejected interventions
do not execute tools.

## Local Commands

```bash
npm install
npm run dev
npm run build
```

The frontend expects:

- Proxy service at `http://localhost:8000`
- Agent runtime at `http://localhost:8002`
- Approval queue at `GET/PATCH http://localhost:8000/v1/interventions`
- Trace data at `GET http://localhost:8000/v1/agents/{agent_id}/traces/runs`

For the full local stack, run `./start-local.sh` from the repository root.
