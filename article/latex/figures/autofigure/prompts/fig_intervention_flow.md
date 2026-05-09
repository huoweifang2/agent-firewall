Style requirements:
Use the uploaded or configured reference image style when available. The target visual language is Researcher/CycleResearcher-style academic process art: a warm paper background, large dashed outer frame, pastel dashed regions, thick tea-gold or gray arrows, compact editable icon cards, document stacks, database cylinders, shield/gate marks, review/score cards, and a larger role/icon block on the left of each lane. Keep it academic and clean, dense but readable, and do not use generic plain boxes only.

Draw a Chinese flowchart for the human intervention approval loop.
Flow: 暂停触发 from Proxy BLOCK or sensitive tool confirmation, 创建审批项 /v1/interventions status=pending, Approvals/Audit 本地控制台审核, approved path to Bridge worker 轮询approved并重放请求, Agent Runtime 验证审批状态, 完成并更新Trace.
Also show rejected path: 状态更新为 rejected, 原请求不执行真实敏感工具.
Keep arrows and labels clear for a thesis figure.
