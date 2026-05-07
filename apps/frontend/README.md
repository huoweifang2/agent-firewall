# Agent-Firewall Frontend

Nuxt/Vuetify console for the OpenClaw safety-shell Agent-Firewall workflow.

`http://localhost:3000` opens Attack Playground. The main navigation then
exposes Approvals / Audit, OpenClaw Sandbox, OpenClaw Agents, Skills & Hooks,
and Trace / Audit.

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

For the full local stack, run `./start-local.sh` from the repository root.
