# 教师意见修改说明

本文档用于辅助手工修改 `/Users/isaachuo/Agent-Firewall/article/docx/霍玮放-本科毕业论文（设计）.docx`。本次不重建 DOCX，也不替换 Word 内图片；文字可按需粘贴到论文中，新生成的 Mermaid 图片位于 `/Users/isaachuo/Agent-Firewall/article/images`。

## 1.2 国内外研究现状修改建议

### 修改目标

原 1.2 节的主要问题是只有方向概括，和参考文献之间的对应关系不够明显。建议将该节改为“三类研究现状 + 本文定位”的结构：

1. 协议与工具生态安全：对应 MCP、OpenClaw、OWASP LLM 风险。
2. Agent 安全评测：对应 AgentDojo、ToolEmu、Agent Security Bench 和 firewall benchmark。
3. 工程防护框架：对应 LLM Guard、Presidio、NeMo Guardrails，以及本文的确定性门控和 Trace 证据链。

引用互证口径建议如下：

| 论述主题 | 建议引用 |
| --- | --- |
| MCP 协议、授权、token audience、token passthrough、OpenClaw/MCP 扩展路径 | `[1][2][15][16]` |
| Prompt injection、insecure output handling、sensitive information disclosure、excessive agency | `[3]` |
| LLM Guard、Presidio、NeMo Guardrails 等检测与防护组件 | `[6][7][8]` |
| AgentDojo、ToolEmu、Agent Security Bench、indirect prompt injection firewall benchmark | `[17][18][19][20]` |

### 可替换正文

下面文字可替换论文第 1.2 节正文。

```markdown
围绕工具调用智能体的安全研究主要集中在协议与工具生态安全、Agent 运行时安全评测、工程防护框架三个方向。

第一类研究关注协议与工具生态安全。MCP 规范将模型、工具和数据源之间的连接方式标准化，使外部能力可以通过统一协议暴露给智能体，但这也使工具描述、能力声明、授权 token、上下文采样和多 Server 编排成为新的安全边界[1][2]。MCP 授权规范强调 access token 必须绑定到目标资源并验证 audience，安全实践文档也明确反对 token passthrough，因为错误的 token 转发会破坏审计、授权和下游安全控制[2]。OpenClaw 的 gateway、Telegram channel、MCP 命令和 mcporter skill 则说明，本机智能体运行时已经具备连接外部入口和工具生态的现实路径[9][10][15][16]。因此，工具调用智能体的安全问题不能只停留在“模型是否生成危险文本”，还需要讨论工具来源、工具权限、工具参数和工具输出能否被独立验证。

第二类研究关注 Agent 运行时安全评测。OWASP LLM Top 10 将 prompt injection、insecure output handling、sensitive information disclosure、insecure plugin design 和 excessive agency 列为 LLM 应用的重要风险[3]，这些风险在具备工具调用能力的 Agent 中会进一步放大。AgentDojo 构建了包含 97 个真实任务和 629 个安全测试的动态评测环境，重点研究外部工具返回的不可信数据如何通过间接提示词注入改变 Agent 行为[17]。ToolEmu 使用 LM-emulated sandbox 模拟高风险工具执行，在 36 个高风险工具和 144 个测试用例上分析工具调用带来的隐私泄露、财务损失和长尾风险[18]。Agent Security Bench 则从 direct prompt injection、indirect prompt injection、memory poisoning、tool usage 等阶段形式化 Agent 攻击与防御，并覆盖多场景、多工具和多类防御方法[19]。这些工作说明，Agent 安全评测需要覆盖输入、模型规划、工具调用、工具输出、记忆和最终回复的完整生命周期，不能只使用单轮文本分类指标。

第三类研究关注工程防护框架。现有工程方案通常组合关键词规则、提示词注入检测、敏感信息识别、RBAC、工具调用确认、输出清洗、请求审计和策略阈值管理。LLM Guard 可用于提示词注入与敏感内容检测，Presidio 侧重 PII 识别与脱敏，NeMo Guardrails 则提供对话安全规则和运行时约束能力[6][7][8]。但是，单独依赖某一种技术存在局限：规则方法速度快但难以覆盖语义伪装，LLM-as-judge 表达能力强但成本和复现性较差，前端提示和模型系统提示也不能强制约束后端真实工具副作用。针对这些不足，本文采用“确定性安全决策优先，必要时接入本地扫描器”的工程路线，把输入扫描、角色权限、参数 Schema、人工审批、工具输出清洗和 Trace 证据链组合为可运行的 Agent-Firewall 系统。

综上，已有研究已经从协议规范、公开评测和工程防护三个层面揭示了工具调用智能体的安全问题，但面向 OpenClaw 本机 skill 调用链路的可执行安全壳、人工审批和 Trace 证据闭环仍需要结合具体系统实现进行验证。本文的工作定位不是提出新的提示词注入检测算法，而是把已有风险认识落实为模型调用前、工具执行前、工具执行后和审计复核四个控制点，并通过项目回归场景、公开基准映射场景、工具链离线回放和本机 OpenClaw/Telegram 复测验证该安全边界。
```

### 如果必须补充国内文献

当前主修改不新增参考文献编号。如果老师明确要求“国内外”必须出现中文论文，可以追加 2 到 3 篇中文综述类文献，再在第一段或第二段后补一句：

```markdown
国内研究也开始围绕大语言模型安全、提示词注入、越狱攻击、隐私泄露和对抗防御进行系统梳理，但多数工作仍以模型输入输出安全为主，对工具执行链路、MCP 类协议边界和本机 Agent 运行时审计的覆盖相对有限。
```

可选中文文献方向：

| 方向 | 可检索题名 |
| --- | --- |
| 大模型安全综述 | 大语言模型安全与隐私风险综述 |
| 攻击与防御综述 | 大语言模型对抗性攻击与防御综述 |
| 安全分类与评估 | 大语言模型安全性：分类、评估、归因、缓解、展望 |

## Trace 部分修改建议

### 是否需要重新跑实验和截图

不建议全量重跑实验。论文已有 11 个工具链离线回放案例和 5 个 OpenClaw/Telegram 真实链路案例，已经足够支撑“至少 10 个 Trace 例子”的修改要求。全量重跑 358 个 JSON 场景或 40 个公开映射场景会改变时间戳和本机状态，反而容易让论文中的实验口径不一致。

如果老师要求截图，建议只补充 Trace/Audit 页面截图作为界面证据，不改变实验分母和结论。优先截图：

1. Trace / Audit 列表页，展示 role、intent、工具数、阻断状态和耗时。
2. `OC-01` 的 Trace-run 详情，展示 input scan、pre-tool、provider execution、post-tool。
3. `OC-02` 或 `TG-02` 的 Trace-run 详情，展示输入层阻断且 `tool_executions=[]`。
4. Compare 中 direct 入口不产生受保护 Trace-run 的对照截图。

### 可补充到 4.8 或 5.7.4 的 Trace 例子表

建议在第 4.8 节“Trace 证据链”末尾或第 5.7.4 节后增加下面表格。该表格超过 10 个例子，既覆盖离线链路，也覆盖真实 OpenClaw/Telegram 链路。

| 编号 | 来源 | Trace 关键证据 | 说明 |
| --- | --- | --- | --- |
| CHAIN-01 | 工具链离线回放 | `pre=['ALLOW','ALLOW']`，`post=['PASS','PASS']`，执行 2 个工具 | 普通客户连续查询，证明多工具正常链路可完整记录。 |
| CHAIN-02 | 工具链离线回放 | `pre=['ALLOW','BLOCK']`，`post=['PASS']` | 同一计划内安全工具继续执行，越权工具在执行前被阻断。 |
| CHAIN-03 | 工具链离线回放 | `pre=['BLOCK']`，无 post-tool | 参数中包含系统提示词抽取模式，真实工具未执行。 |
| CHAIN-06 | 工具链离线回放 | `pre=['REQUIRE_CONFIRMATION']`，无 post-tool | critical 工具进入人工确认队列，证明高敏操作不会自动执行。 |
| CHAIN-07 | 工具链离线回放 | `pre=['ALLOW']`，`post=['REDACT']` | 审批后重放，工具结果中的密钥和连接串被清洗。 |
| CHAIN-08 | 工具链离线回放 | `pre=['ALLOW']`，`post=['REDACT']` | 支持角色读取资料后，邮箱和电话被脱敏。 |
| CHAIN-09 | 工具链离线回放 | `pre=['ALLOW']`，`post=['BLOCK']` | 工具返回的恶意知识库内容被 post-tool gate 阻断。 |
| CHAIN-10 | 工具链离线回放 | `pre=['MODIFY']`，`post=['PASS']` | 超长参数被截断后继续执行，证明 MODIFY 路径可追踪。 |
| CHAIN-11 | 工具链离线回放 | `pre=['ALLOW']`，`post=['REDACT']`，记录委派事件 | 子 Agent 委派被视为受保护工具，委派结果仍走输出清洗。 |
| OC-01 | `/agent/chat` 真实 OpenClaw 链路 | `tool_calls=1`，`openclaw_summarize` 执行，post-tool `TRUNCATE` | 完整经过输入扫描、pre-tool、OpenClaw provider、post-tool 和 Trace-run 持久化。 |
| OC-02 | `/agent/chat` 真实 OpenClaw 链路 | `risk_score=1.0`，`blocked_reason=Denylist match`，`tool_executions=[]` | 泄露 system prompt/API key 的请求在模型调用前被阻断。 |
| TG-01 | Telegram Bridge 真实链路 | `ALLOW`，调用 `openclaw_summarize`，post-tool `REDACT` | Telegram 入口可以进入受保护 OpenClaw skill 链路，结果经输出清洗。 |
| TG-03 | Telegram Bridge 真实链路 | `ALLOW`，无工具执行，最终回复回显攻击标记 | 间接注入文本未触发工具执行，但暴露输出回显治理不足。 |

### 可粘贴补充段落

```markdown
为了避免 Trace 只停留在字段定义层面，本文进一步从离线回放和真实链路复测中选取 13 个代表性 Trace 例子进行说明。CHAIN-01 至 CHAIN-11 覆盖多工具连续调用、部分执行、参数注入阻断、高敏确认、审批后重放、PII/密钥清洗、间接注入阻断、长参数修改和子 Agent 委派清洗等路径；OC-01、OC-02 和 TG-01、TG-03 则覆盖 `/agent/chat` 与 Telegram Bridge 进入受保护 OpenClaw 链路后的真实 Trace-run。上述例子说明，Trace 不是普通文本日志，而是能够记录输入扫描、工具计划、执行前门控、provider 执行、执行后清洗和最终回复的结构化证据。
```

## Mermaid 图片重绘说明

本次需要重绘的 Mermaid 图如下，输出目录均为 `/Users/isaachuo/Agent-Firewall/article/images`：

| 图片 | 说明 |
| --- | --- |
| `fig_2_1_trust_boundaries.png` | 系统资产流转与主要信任边界 |
| `fig_3_1_architecture.png` | Agent-Firewall 总体架构 |
| `fig_4_1_method_overview.png` | 方法总览与工具调用安全状态流 |
| `fig_4_2_scan_pipeline.png` | `/v1/scan` scan-only 检测流水线 |
| `fig_4_3_risk_decision.png` | 风险聚合与决策规则 |
| `fig_4_4_agent_runtime_graph.png` | Agent Runtime 运行图 |
| `fig_4_5_pre_tool_gate.png` | pre-tool gate 检查链与四类决策 |
| `fig_4_6_post_tool_gate.png` | post-tool gate 输出清洗流程 |
| `fig_4_7_openclaw_bridge.png` | OpenClaw provider 受保护桥接 |
| `fig_4_8_intervention_state.png` | intervention 审批状态机 |
| `fig_4_9_trace_evidence.png` | Trace 审计证据链结构 |

已调整的重绘口径：

1. Mermaid 字体从 22px 提升到 32px。
2. 节点边框从 2px 提升到 3px。
3. 节点间距、层级间距和画布 padding 增大，避免 Word 缩放后文字过小。
4. `fig_4_7_openclaw_bridge` 和 `fig_4_9_trace_evidence` 改为多行布局，避免横向过宽导致插入 Word 后被压缩。
5. 只重绘 Mermaid 流程图，不处理前端截图和第 5 章统计图。

重绘命令：

```bash
python3 /Users/isaachuo/Agent-Firewall/article/generate_mermaid_flowcharts.py
```

尺寸检查命令：

```bash
for f in /Users/isaachuo/Agent-Firewall/article/images/fig_2_1_trust_boundaries.png \
  /Users/isaachuo/Agent-Firewall/article/images/fig_3_1_architecture.png \
  /Users/isaachuo/Agent-Firewall/article/images/fig_4_*.png; do
  printf '%s ' "$f"
  sips -g pixelWidth -g pixelHeight "$f" 2>/dev/null | awk '/pixelWidth|pixelHeight/{printf "%s ", $2} END{print ""}'
done
```

手工替换 Word 图片时，建议优先替换第四章所有 Mermaid 图，尤其是 `fig_4_7_openclaw_bridge.png` 和 `fig_4_9_trace_evidence.png`，因为这两张原图横向压缩最明显。
