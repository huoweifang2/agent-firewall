Style requirements:
Use the uploaded or configured reference image style when available. The target visual language is a paper-style process diagram: a large dashed outer frame, pastel horizontal lanes, dashed rounded lane boundaries, thick light-gray arrows, compact icon-like cards, a larger illustrated role/icon block on the left of each lane, and dense but readable labels. Keep it academic and clean; do not use generic plain boxes only.

Draw a horizontal flowchart in Chinese for the Proxy Service scan-only pipeline.
Nodes in order: parse 消息规范化, intent 攻击意图分类, rules denylist/长度/编码, scanners 本地扫描, decision 风险聚合, audit 请求日志.
From decision branch to ALLOW 继续Agent运行, MODIFY 脱敏/改写, BLOCK 暂停或拒绝.
Make clear that the proxy does not call the LLM and returns deterministic ALLOW/MODIFY/BLOCK decisions.
