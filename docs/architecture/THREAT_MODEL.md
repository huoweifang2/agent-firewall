# Threat Model

## Assets

- Telegram bot token and allowed Telegram user IDs.
- DeepSeek/OpenClaw credentials in local config.
- OpenClaw skills, hooks, MCP providers, and local files they can reach.
- Agent-Firewall SQLite audit database.
- User messages and tool outputs in traces.

## Trust Boundaries

- Telegram input is untrusted.
- LLM tool plans are untrusted until the pre-tool gate approves them.
- Tool output is untrusted until the post-tool gate scans it.
- Browser/operator actions are trusted only for local development on `localhost:3000`.
- Raw OpenClaw direct access is trusted only for Compare and must not be used as the Telegram path.

## Primary Risks

- Prompt injection in Telegram messages.
- Tool abuse through model-proposed tool calls.
- Sensitive OpenClaw skill execution without approval.
- MCP endpoint misuse or unexpected output injection.
- Secret leakage in logs, traces, UI, or error messages.
- Duplicate Telegram consumers polling the same bot.

## Controls

- Telegram Bridge allowlist from `~/.openclaw/openclaw.json`.
- Proxy `/v1/scan` before model execution.
- Runtime RBAC and tool allowlists.
- Argument schema validation and injection scanning.
- Budget and rate limits.
- Confirmation gates for sensitive tools.
- Post-tool PII/secret/injection scanning.
- Redaction in OpenClaw diagnostics and trace previews.
- `/v1/interventions` approval queue for blocked or confirmation-gated requests.

## Residual Risk

Agent-Firewall reduces the blast radius of tool-calling agents but does not make arbitrary tools safe. High-impact OpenClaw skills and MCP providers should remain confirmation-gated and reviewed in the Approvals / Audit page.
