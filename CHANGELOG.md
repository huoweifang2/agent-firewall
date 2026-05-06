# Changelog

## Current Focus

This workspace is now maintained as a Telegram-first Agent-Firewall project.

- Primary path: Telegram Bot -> Agent-Firewall Telegram Bridge -> proxy scan -> runtime tool gates -> OpenClaw skill/MCP provider -> Telegram reply.
- Local console: `localhost:3000` opens Attack Playground, with Approvals / Audit available for paused Telegram traffic.
- Python services are managed with `uv`; local persistence defaults to SQLite.
- OpenClaw skills and MCP tools are imported as protected providers and pass through RBAC, argument scanning, limits, confirmation, post-tool filtering, and trace recording.
- Legacy infrastructure and demo artifacts have been removed from the active product path.

Older generated release notes were intentionally replaced because they described a different product shape.
