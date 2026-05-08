Style requirements:
Use the uploaded or configured reference image style when available. The target visual language is a paper-style process diagram: a large dashed outer frame, pastel horizontal lanes, dashed rounded lane boundaries, thick light-gray arrows, compact icon-like cards, a larger illustrated role/icon block on the left of each lane, and dense but readable labels. Keep it academic and clean; do not use generic plain boxes only.

Draw a state-machine style Chinese diagram for tool-call gating in Agent-Firewall.
States: 工具计划生成, pre-tool检查, ALLOW, MODIFY, BLOCK, REQUIRE_CONFIRMATION, 审批通过重放, 工具执行, post-tool检查, PASS, REDACT, BLOCK_OUTPUT, Trace落盘, 最终回复.
Show that BLOCK and REQUIRE_CONFIRMATION stop execution before real tools, while REDACT/BLOCK_OUTPUT happen after tool execution before LLM context.
Use flowchart cards, guarded arrows, pastel swimlanes, and thesis-neutral terminology.
