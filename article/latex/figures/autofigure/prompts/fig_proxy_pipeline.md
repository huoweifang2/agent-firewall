Style requirements:
Use the uploaded or configured reference image style when available. The target visual language is Researcher/CycleResearcher-style academic process art: a warm paper background, large dashed outer frame, pastel dashed regions, thick tea-gold or gray arrows, compact editable icon cards, document stacks, database cylinders, shield/gate marks, review/score cards, and a larger role/icon block on the left of each lane. Keep it academic and clean, dense but readable, and do not use generic plain boxes only.

Draw a horizontal flowchart in Chinese for the Proxy Service scan-only pipeline.
Nodes in order: parse 消息规范化, intent 攻击意图分类, rules denylist/长度/编码, scanners 本地扫描, decision 风险聚合, audit 请求日志.
From decision branch to ALLOW 继续Agent运行, MODIFY 脱敏/改写, BLOCK 暂停或拒绝.
Make clear that the proxy does not call the LLM and returns deterministic ALLOW/MODIFY/BLOCK decisions.
