"""Generate paper figures for artical.tex.

The script is intentionally self-contained: it does not call external APIs,
PostgreSQL, OpenClaw, or the running web stack.  All values are copied from
the reproducible offline checks and repository benchmark report described in
the thesis.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

try:
    import scienceplots  # noqa: F401

    plt.style.use(["science", "no-latex"])
except Exception:
    plt.style.use("default")


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)


def configure_fonts() -> None:
    candidates = [
        "Songti SC",
        "PingFang SC",
        "Heiti SC",
        "Arial Unicode MS",
        "SimSong",
        "Noto Sans CJK SC",
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            plt.rcParams["font.family"] = "sans-serif"
            break
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["ps.fonttype"] = 42
    plt.rcParams["figure.dpi"] = 160
    plt.rcParams["savefig.dpi"] = 320


def box(ax, xy, w, h, text, fc="#f8fafc", ec="#334155", fs=9, lw=1.2):
    patch = FancyBboxPatch(
        xy,
        w,
        h,
        boxstyle="round,pad=0.03,rounding_size=0.02",
        fc=fc,
        ec=ec,
        lw=lw,
    )
    ax.add_patch(patch)
    ax.text(
        xy[0] + w / 2,
        xy[1] + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fs,
        linespacing=1.35,
    )
    return patch


def arrow(ax, start, end, color="#475569", lw=1.2, rad=0.0):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=11,
            lw=lw,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
        )
    )


def save(fig, name: str) -> None:
    fig.savefig(OUT / name, bbox_inches="tight")
    plt.close(fig)


def architecture() -> None:
    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")

    box(
        ax,
        (3.4, 6.05),
        3.2,
        0.62,
        "Nuxt 4 + Vuetify Web 控制台\nPlayground / Agents / Traces / Analytics",
        "#e0f2fe",
    )
    box(
        ax,
        (0.5, 4.7),
        3.2,
        0.85,
        "Proxy Firewall API\nFastAPI :8000\n9 节点检测流水线",
        "#dcfce7",
    )
    box(
        ax,
        (6.3, 4.7),
        3.2,
        0.85,
        "Agent Runtime API\nFastAPI :8002\n11 节点工具调用防护图",
        "#fef3c7",
    )
    box(
        ax,
        (0.8, 3.05),
        2.6,
        0.75,
        "本地扫描器\nRules / Intent\nLLM Guard / Presidio / NeMo",
        "#f1f5f9",
    )
    box(
        ax,
        (3.95, 3.05),
        2.1,
        0.75,
        "PostgreSQL + Redis\n策略 / 日志 / Trace",
        "#f1f5f9",
    )
    box(ax, (6.6, 3.05), 2.6, 0.75, "工具提供者\nInternal / MCP / OpenClaw", "#f1f5f9")
    box(ax, (0.9, 1.35), 2.4, 0.7, "LLM Provider\nLiteLLM 路由", "#f8fafc")
    box(ax, (3.8, 1.35), 2.4, 0.7, "Langfuse 可选导出\n结构化 Span", "#f8fafc")
    box(ax, (6.7, 1.35), 2.4, 0.7, "Subagents\n创建 / 绑定 / 委派", "#f8fafc")

    arrow(ax, (4.4, 6.05), (2.5, 5.55))
    arrow(ax, (5.6, 6.05), (7.5, 5.55))
    arrow(ax, (2.1, 4.7), (2.1, 3.8))
    arrow(ax, (7.9, 4.7), (7.9, 3.8))
    arrow(ax, (3.7, 5.1), (6.3, 5.1))
    arrow(ax, (2.1, 3.05), (2.1, 2.05))
    arrow(ax, (5.0, 3.05), (5.0, 2.05))
    arrow(ax, (7.9, 3.05), (7.9, 2.05))
    ax.text(
        5,
        0.55,
        "设计原则：确定性安全决策与 LLM 业务推理解耦，Proxy 层管控文本风险，Agent 层管控能力边界。",
        ha="center",
        fontsize=9,
    )
    save(fig, "fig_architecture.pdf")


def proxy_pipeline() -> None:
    fig, ax = plt.subplots(figsize=(10.5, 3.2))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3)
    ax.axis("off")
    nodes = [
        ("parse\n规范化", "#e0f2fe"),
        ("intent\n意图分类", "#dbeafe"),
        ("rules\n规则命中", "#dcfce7"),
        ("scanners\n并行扫描", "#fef3c7"),
        ("decision\n风险聚合", "#fee2e2"),
        ("transform\n脱敏改写", "#f3e8ff"),
        ("llm_call\n模型调用", "#e2e8f0"),
        ("output_filter\n输出过滤", "#fde68a"),
        ("logging\n审计日志", "#e5e7eb"),
    ]
    x0 = 0.25
    centers = []
    for i, (label, color) in enumerate(nodes):
        x = x0 + i * 1.28
        box(ax, (x, 1.35), 1.0, 0.62, label, color, fs=8)
        centers.append((x + 0.5, 1.66))
        if i:
            arrow(ax, (centers[i - 1][0] + 0.5, 1.66), (x, 1.66), lw=1.0)
    box(ax, (5.25, 0.35), 1.25, 0.45, "BLOCK\n不调用模型", "#fecaca", fs=8)
    arrow(ax, (5.25, 1.35), (5.9, 0.8), color="#dc2626", rad=0.05)
    ax.text(
        5.2,
        2.5,
        "Proxy Firewall：请求进入模型前完成确定性拦截，ALLOW/MODIFY 才进入模型调用路径",
        ha="center",
        fontsize=10,
    )
    save(fig, "fig_proxy_pipeline.pdf")


def agent_pipeline() -> None:
    fig, ax = plt.subplots(figsize=(10.8, 5.4))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis("off")
    top = [
        ("input\n会话/限额", 0.25),
        ("intent\n用户意图", 1.55),
        ("policy_check\n策略加载", 2.85),
        ("tool_router\n工具规划", 4.15),
        ("pre_tool_gate\nRBAC/Schema/限额", 5.45),
        ("tool_executor\n工具执行", 7.0),
        ("post_tool_gate\n输出清洗", 8.3),
        ("llm_call\nProxy 扫描+模型", 9.6),
        ("response\n响应格式化", 10.9),
    ]
    for i, (label, x) in enumerate(top):
        box(
            ax,
            (x, 3.55),
            1.05,
            0.72,
            label,
            "#f8fafc" if i not in (4, 6, 7) else "#fee2e2",
            fs=7.4,
        )
        if i:
            arrow(ax, (top[i - 1][1] + 1.05, 3.91), (x, 3.91), lw=1.0)
    box(
        ax,
        (5.55, 2.15),
        1.45,
        0.52,
        "confirmation_response\n敏感操作人工确认",
        "#fef3c7",
        fs=7.6,
    )
    box(ax, (9.45, 2.15), 1.05, 0.52, "memory\n会话持久化", "#e0f2fe", fs=7.6)
    box(ax, (10.85, 2.15), 1.05, 0.52, "trace\n审计轨迹", "#e0f2fe", fs=7.6)
    arrow(ax, (5.95, 3.55), (6.25, 2.67), color="#d97706")
    arrow(ax, (11.4, 3.55), (10.0, 2.67), color="#2563eb", rad=0.18)
    arrow(ax, (10.5, 2.41), (10.85, 2.41), color="#2563eb")

    box(
        ax,
        (0.7, 0.7),
        3.0,
        0.65,
        "第一道防线：pre-tool gate\n调用前判定“能不能调用、参数能不能用”",
        "#dcfce7",
        fs=8.5,
    )
    box(
        ax,
        (4.45, 0.7),
        3.0,
        0.65,
        "第二道防线：post-tool gate\n调用后判定“结果能不能进入 LLM 上下文”",
        "#fef3c7",
        fs=8.5,
    )
    box(
        ax,
        (8.2, 0.7),
        3.0,
        0.65,
        "第三道防线：proxy firewall\n模型调用前再次扫描用户输入",
        "#dbeafe",
        fs=8.5,
    )
    save(fig, "fig_agent_pipeline.pdf")


def risk_scoring() -> None:
    labels = ["Intent", "Denylist", "LLM Guard", "NeMo", "Presidio", "Rules Boost"]
    weights = [0.40, 0.80, 0.80, 0.70, 0.50, 0.30]
    colors = ["#60a5fa", "#f87171", "#fbbf24", "#34d399", "#a78bfa", "#94a3b8"]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.bar(labels, weights, color=colors, edgecolor="#334155", linewidth=0.8)
    ax.set_ylabel("风险贡献上限或权重")
    ax.set_ylim(0, 1.0)
    ax.set_title("风险评分聚合：多信号加权后按策略阈值决策")
    for i, v in enumerate(weights):
        ax.text(i, v + 0.03, f"{v:.2f}", ha="center", fontsize=8)
    ax.axhline(0.7, color="#dc2626", lw=1.2, ls="--", label="balanced 阈值 0.70")
    ax.legend(frameon=False, loc="upper right")
    save(fig, "fig_risk_scoring.pdf")


def redteam_categories() -> None:
    data = [
        ("Prompt Injection", 100),
        ("Tool Abuse", 100),
        ("Data Exfiltration", 100),
        ("Resource Exhaustion", 100),
        ("Secrets Detection", 16.7),
        ("Obfuscation", 15.4),
        ("Multi-Language", 16.7),
        ("Payload Splitting", 33.3),
        ("RAG Poisoning", 50.0),
        ("Advanced Multi-Turn", 66.7),
        ("Confused Deputy", 71.4),
        ("Social Engineering", 70.0),
    ]
    labels, values = zip(*data)
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    bars = ax.barh(
        range(len(values)),
        values,
        color=[
            "#22c55e" if v >= 90 else "#f59e0b" if v >= 60 else "#ef4444"
            for v in values
        ],
    )
    ax.set_yticks(range(len(labels)), labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 105)
    ax.set_xlabel("检出率 / %")
    ax.set_title("离线红队复测中代表性类别检出率")
    for bar, value in zip(bars, values):
        ax.text(
            value + 1,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.1f}%",
            va="center",
            fontsize=8,
        )
    save(fig, "fig_redteam_categories.pdf")


def benchmark_compare() -> None:
    labels = ["当前离线复测\n轻量扫描器", "历史完整扫描器\nBENCHMARK.md"]
    detection = [73.7, 97.9]
    false_positive = [0.0, 0.0]
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    x = range(len(labels))
    ax.bar(
        [i - 0.17 for i in x],
        detection,
        width=0.34,
        label="攻击检出率",
        color="#2563eb",
    )
    ax.bar(
        [i + 0.17 for i in x],
        false_positive,
        width=0.34,
        label="误报率",
        color="#f97316",
    )
    ax.set_xticks(list(x), labels)
    ax.set_ylim(0, 105)
    ax.set_ylabel("比例 / %")
    ax.set_title("离线复测与完整扫描器基准对比")
    for i, v in enumerate(detection):
        ax.text(i - 0.17, v + 2, f"{v:.1f}%", ha="center", fontsize=8)
    for i, v in enumerate(false_positive):
        ax.text(i + 0.17, v + 2, f"{v:.1f}%", ha="center", fontsize=8)
    ax.legend(frameon=False)
    save(fig, "fig_benchmark_compare.pdf")


def latency_breakdown() -> None:
    nodes = ["parse", "intent", "rules", "scanners", "decision"]
    current = [0.00, 0.03, 0.01, 0.05, 0.00]
    full = [0.01, 0.02, 0.02, 47.33, 0.01]
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    x = list(range(len(nodes)))
    ax.bar(
        [i - 0.18 for i in x],
        current,
        width=0.36,
        label="当前离线 p50/ms",
        color="#38bdf8",
    )
    ax.bar(
        [i + 0.18 for i in x],
        full,
        width=0.36,
        label="完整扫描器 p50/ms",
        color="#f97316",
    )
    ax.set_xticks(x, nodes)
    ax.set_ylabel("节点耗时 / ms")
    ax.set_yscale("symlog", linthresh=0.1)
    ax.set_title("Pre-LLM pipeline 节点耗时分解")
    ax.legend(frameon=False)
    save(fig, "fig_latency_breakdown.pdf")


def delegation_cases() -> None:
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis("off")
    lanes = [
        ("User", 1.0),
        ("Main Agent", 3.1),
        ("Pre/Post Gates", 5.2),
        ("Subagent / Tool", 7.3),
        ("Trace Store", 9.2),
    ]
    for label, x in lanes:
        ax.text(x, 7.55, label, ha="center", fontsize=9, fontweight="bold")
        ax.plot([x, x], [0.7, 7.25], color="#cbd5e1", lw=1)

    events = [
        (6.9, "1 正常订单查询", 1.0, 3.1, "#2563eb"),
        (6.25, "2 RBAC 拦截密钥", 3.1, 5.2, "#dc2626"),
        (5.6, "3 参数注入阻断", 3.1, 5.2, "#dc2626"),
        (4.95, "4 上下文外泄阻断", 3.1, 5.2, "#dc2626"),
        (4.3, "5 重复失败升级", 3.1, 5.2, "#dc2626"),
        (3.65, "6 长参数清洗", 5.2, 7.3, "#16a34a"),
        (3.0, "7 敏感工具确认", 5.2, 3.1, "#d97706"),
        (2.35, "8 创建子智能体", 3.1, 7.3, "#7c3aed"),
        (1.7, "9 委派支付分析", 3.1, 7.3, "#7c3aed"),
        (1.05, "10 Trace 审计落盘", 5.2, 9.2, "#0f766e"),
    ]
    for y, label, x1, x2, color in events:
        arrow(ax, (x1, y), (x2, y), color=color, lw=1.25)
        ax.text((x1 + x2) / 2, y + 0.11, label, ha="center", fontsize=8, color=color)
    ax.set_title("Agent/subagent 调用与委派链案例", fontsize=11)
    save(fig, "fig_delegation_cases.pdf")


def main() -> None:
    configure_fonts()
    architecture()
    proxy_pipeline()
    agent_pipeline()
    risk_scoring()
    redteam_categories()
    benchmark_compare()
    latency_breakdown()
    delegation_cases()


if __name__ == "__main__":
    main()
