# Agent-Firewall

Agent-Firewall 现在收敛为一个 **Telegram 优先的个人 OpenClaw Bot 安全网关**。用户只从 Telegram 对话；`http://localhost:3000` 是后台控制台，用来做攻击演练、审批、日志追踪，以及绑定 OpenClaw skill / MCP 工具。

## 主运行链路

```text
Telegram Bot
  -> apps/agent Telegram Bridge
  -> apps/proxy-service /v1/scan
  -> apps/agent runtime graph
  -> pre-tool gate
  -> OpenClaw skill / MCP provider
  -> post-tool gate
  -> trace + audit log
  -> Telegram reply
```

如果输入被拦截，或敏感工具需要确认，Telegram 会先收到“等待控制台审批”的回复；审批项会出现在 `localhost:3000` 的 **Approvals / Audit** 页面。审批通过后，Agent 会继续执行并把最终结果发回 Telegram。

## 本地启动

需要：

- `uv`
- Node.js 和 npm
- 已配置好的本机 OpenClaw CLI
- `~/.openclaw/openclaw.json` 中已有 Telegram bot token

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
- **Approvals / Audit**：处理 Telegram 输入拦截和工具确认。
- **Skills & Hooks**：发现 OpenClaw skills/hooks，并把 eligible skill 绑定成受保护工具。
- **Trace / Audit**：查看输入扫描、工具计划、pre-tool gate、工具执行、post-tool gate 和最终回复。
- **Runtime Settings**：查看脱敏后的 OpenClaw、DeepSeek、Telegram Bridge、gateway 状态。

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
- `/agent/openclaw/direct` 只用于 Compare 对照，不是 Telegram 主链路。
- Telegram 对话中的 tool use、OpenClaw skill、MCP 调用都应经过 Agent-Firewall runtime graph 和双重工具门控。
