# Agent-Firewall

Agent-Firewall 是一个毕业设计项目，致力于为支持工具调用（Tool-Calling）的 AI 智能体（Agents）提供安全护栏与检测功能。其核心目标是能够探测并拦截提示词注入（Prompt Injection）以及未经授权的工具滥用，通过确定性的安全策略进行强制拦截，使大语言模型（LLM）本身脱离这一安全决策闭环。

*👉 [English Version](README.md)*

---

## 快速入门与本地开发

### 环境要求
- **Docker & Docker Compose**
- **uv** (用于 Python 依赖管理): `curl -LsSf https://astral.sh/uv/install.sh | sh` (或 `brew install uv`)
- **Node.js & npm** (用于前端)

### 启动项目栈

测试或开发该项目最常见的方式是并发启动所有本地应用程序服务：

1. **克隆仓库：**
   ```bash
   git clone https://github.com/Szesnasty/agent-firewall.git
   cd agent-firewall
   ```

2. **安装依赖：**
   ```bash
   make setup
   ```

3. **配置 API 密钥 (API Keys)：**
   启动应用前，请在 `apps/agent/.env` 与 `apps/proxy-service/.env`（如果不存在请自行创建）中填入你所使用的模型与 OpenClaw 桥接配置。例如：
   ```env
   # .env 示例
   DEEPSEEK_API_KEY="your-deepseek-api-key"
   OPENCLAW_BIN="openclaw"
   OPENCLAW_AGENT_ID="coder"
   ```

4. **启动完整开发环境：**
   ```bash
   ./start-local.sh
   ```
   *(该命令会并发启动后端代理、Agent 服务、前端界面，以及必需的 Docker 基础设施如 DB, Redis, Langfuse 等)*

5. **访问前端平台：**
   在浏览器中打开 **http://localhost:3000**。

> 注意：如果想要干净地关闭服务与基础设施，请先在终端中使用 `Ctrl+C` 停止应用程序进程，随后运行 `make down` 关闭 Docker 后端容器。

---

## 核心特性

### 🛡️ 代理防火墙 (Proxy Firewall)
每一次调用 LLM 时，都会在本地极速执行 5 层检测拦截（无外部 API 请求，约 50 毫秒开销）：
- **规则 (Rules)：** 关键词黑名单、长度限制、编码检查
- **意图分类器 (Intent classifier)：** 包含用于对攻击类型进行归类的正则表达式
- **LLM Guard：** 基于 DeBERTa 的注入检测与 DistilBERT 处理毒性文本
- **Presidio 隐私擦除 (PII)：** 抹除敏感实体（姓名、邮箱、信用卡、电话号码等）
- **NeMo Guardrails：** 基于 FastEmbed 的轻量级向量语义相似度检测

### 🔍 智能体运行层约束 (Agent-Level Enforcement)
在智能体执行工具调用的环节，本系统设置了两道关卡拦截并强制执行安全策略：
- **工具生态集成 (Tool Integrations)：** 基于 OpenClaw skill 桥接，将外部能力挂载为受 Agent-Firewall 管控的工具。
- **前置评估 (Pre-tool gate)：** 角色权限控制 (RBAC)、参数注入检测、额度预算、用户二次确认
- **后置评估 (Post-tool gate)：** PII 数据清洗、API 密钥/凭据泄露反扫、防间接注入

### 📊 安全扫描 (Security Scan)
将精选的攻击测试用例发往一个兼容 OpenAI 格式的目标端点，从而测试当前漏洞，并可确定地量化护栏的实际拦截有效性。

---

## 性能指标

| 测试指标 | 表现数据 |
|---|---|
| 攻击拦截率 | **97.9%** (331 / 338) |
| 误报率 (False positive rate) | **0 / 20** (无安全提示词被误拦截) |
| 管道执行开销 | 每次请求延时增加约 **~50 毫秒** (balanced 均衡策略下) |
| 内存占用 | 约 **~1.1 GB RAM** (所有扫描模型加载后) |

→ [查看完整内部测试基准 (BENCHMARK)](BENCHMARK.md) · [JailbreakBench 防御测试结果](BENCHMARK_JAILBREAKBENCH.md)

---

## 已知局限性
Agent-Firewall 目前是一个关于支持工具调用的 Agent 系统的验证性安全实验。它能够降低实际应用中的很大风险，但并不能完全消除它们（例如某些绕过了正则表达式匹配的复杂语义级伪装攻击）。
