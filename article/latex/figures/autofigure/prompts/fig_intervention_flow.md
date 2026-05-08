Style requirements:
Use the uploaded or configured reference image style when available. The target visual language is a paper-style process diagram: a large dashed outer frame, pastel horizontal lanes, dashed rounded lane boundaries, thick light-gray arrows, compact icon-like cards, a larger illustrated role/icon block on the left of each lane, and dense but readable labels. Keep it academic and clean; do not use generic plain boxes only.

Draw a Chinese flowchart for the human intervention approval loop.
Flow: 暂停触发 from Proxy BLOCK or sensitive tool confirmation, 创建审批项 /v1/interventions status=pending, Approvals/Audit 本地控制台审核, approved path to Bridge worker 轮询approved并重放请求, Agent Runtime 验证审批状态, 完成并更新Trace.
Also show rejected path: 状态更新为 rejected, 原请求不执行真实敏感工具.
Keep arrows and labels clear for a thesis figure.
