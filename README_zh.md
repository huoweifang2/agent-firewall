# Agent-Firewall

Agent-Firewall 是包裹在本机 OpenClaw runtime 外侧的安全壳/中间层。它位于消息入口适配器与 OpenClaw/MCP/Internal 工具之间，负责输入扫描、运行时工具门控、人工审批、Trace/Audit 证据链和受保护能力接入。

Telegram 是当前已经实现的消息入口适配器，用于接入真实聊天流量，但不是项目核心。项目核心边界是 Agent-Firewall 对 OpenClaw 工具执行链路的安全控制。

## 受保护运行链路

```text
Message ingress adapter
  -> apps/agent protected runtime
  -> apps/proxy-service /v1/scan
  -> Agent runtime gates
  -> OpenClaw skill / MCP provider
  -> post-tool gate
  -> trace + audit log
  -> reply channel
```

如果输入被拦截，或敏感工具需要确认，请求会被暂停；审批项会出现在 `localhost:3000` 的 **Approvals / Audit** 页面。审批通过后，受保护 runtime 会继续执行并通过原始入口适配器返回结果。

## 本地启动

需要：

- `uv`
- Node.js 和 npm
- 已配置好的本机 OpenClaw CLI
- 只有启用 Telegram Bridge 入口适配器时，才需要 `~/.openclaw/openclaw.json` 中已有 Telegram bot token

安装依赖：

```bash
make setup
```

创建本地配置：

```bash
cp apps/proxy-service/.env.example apps/proxy-service/.env.local
cp apps/agent/.env.example apps/agent/.env.local
```

启动：

```bash
./start-local.sh
```

访问：

- 前端：`http://localhost:3000`
- Proxy：`http://localhost:8000`
- Agent：`http://localhost:8002`

默认数据库是 `~/.openclaw/agent-firewall.sqlite`。默认本地路径不需要 Docker、Redis 或 Langfuse。

## 页面

- **Attack Playground**：默认首页和左侧第一项，用于手动攻击测试。
- **Approvals / Audit**：处理输入拦截和工具确认。
- **Skills & Hooks**：发现 OpenClaw skills/hooks，并把 eligible skill 绑定成受保护工具。
- **Trace / Audit**：查看输入扫描、工具计划、pre-tool gate、工具执行、post-tool gate 和最终回复。
- **Runtime Settings**：查看脱敏后的 OpenClaw、DeepSeek、入口适配器和 gateway 状态。

## 常用命令

```bash
make lint
make test
make frontend-build
```

OpenClaw 检查：

```bash
openclaw status --json --no-usage
openclaw agents list --json
openclaw skills list --json
openclaw hooks list --json
```

## 安全边界

- 不要提交真实 API key、Telegram token、gateway token 或 `.env.local`。
- `/agent/openclaw/direct` 只用于 Compare 对照，不是受保护运行链路。
- OpenClaw skill、MCP 调用以及消息入口触发的 tool use 都应经过 Agent-Firewall runtime graph 和双重工具门控。
