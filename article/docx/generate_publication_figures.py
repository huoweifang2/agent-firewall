#!/usr/bin/env python3
"""Generate publication-quality thesis figures for the DOCX build.

Figures are deterministic and use only repository-local scenario data plus
fixed architecture facts documented in the thesis. The output names match the
figure labels consumed by build_thesis_docx.py.
"""

from __future__ import annotations

import json
import textwrap
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

try:
    import scienceplots  # noqa: F401

    plt.style.use(["science", "no-latex", "grid"])
except Exception:
    plt.style.use("default")


ARTICLE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = ARTICLE_DIR.parent
OUT = ARTICLE_DIR / "docx" / "generated_figures"
SCENARIO_DIR = REPO_ROOT / "apps" / "proxy-service" / "data" / "scenarios"
OUT.mkdir(parents=True, exist_ok=True)

INK = "#1f2937"
MUTED = "#64748b"
LINE = "#334155"
BLUE = "#dbeafe"
GREEN = "#dcfce7"
YELLOW = "#fef3c7"
RED = "#fee2e2"
PURPLE = "#ede9fe"
GRAY = "#f1f5f9"
TEAL = "#ccfbf1"
ORANGE = "#ffedd5"
PALETTE = [BLUE, GREEN, YELLOW, RED, PURPLE, TEAL, ORANGE, GRAY]


def configure() -> None:
    candidates = [
        "Songti SC",
        "PingFang SC",
        "Heiti SC",
        "Arial Unicode MS",
        "Noto Sans CJK SC",
        "SimSong",
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = "sans-serif"
            plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            break
    plt.rcParams.update(
        {
            "axes.unicode_minus": False,
            "figure.dpi": 160,
            "savefig.dpi": 320,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.edgecolor": LINE,
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "text.color": INK,
        }
    )


def wrap(label: str, width: int = 14) -> str:
    return "\n".join(textwrap.wrap(label, width=width, break_long_words=False))


def save(fig, name: str) -> None:
    fig.savefig(OUT / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def box(ax, xy, wh, text, fc=GRAY, fs=9.5, lw=1.15):
    x, y = xy
    w, h = wh
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.025,rounding_size=0.055",
        fc=fc,
        ec=LINE,
        lw=lw,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, linespacing=1.28, fontweight="semibold")
    return patch


def arrow(ax, start, end, color=LINE, lw=1.25, rad=0.0):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=12,
            lw=lw,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
        )
    )


def scenario_groups() -> tuple[list[tuple[str, int]], dict[str, Counter]]:
    totals: list[tuple[str, int]] = []
    decisions: dict[str, Counter] = {}
    for name in ["playground", "agent"]:
        path = SCENARIO_DIR / f"{name}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        file_counter = Counter()
        count = 0
        for group in data:
            items = group.get("items", [])
            count += len(items)
            totals.append((group["label"], len(items)))
            for item in items:
                file_counter[item.get("expectedDecision", "UNKNOWN")] += 1
        decisions[name] = file_counter
        assert count > 0
    return totals, decisions


def title(ax, text: str) -> None:
    ax.text(0.02, 0.94, text, transform=ax.transAxes, fontsize=13.5, fontweight="bold", va="top")


def flow_figure(name: str, title_text: str, nodes: list[str], note: str, colors=None):
    colors = colors or PALETTE
    fig, ax = plt.subplots(figsize=(10.6, 4.7))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    title(ax, title_text)
    n = len(nodes)
    w = min(1.52, 8.7 / n)
    gap = (9.1 - n * w) / max(1, n - 1)
    y = 2.7
    h = 0.82
    boxes = []
    for i, node in enumerate(nodes):
        x = 0.45 + i * (w + gap)
        boxes.append((x, y, w, h))
        box(ax, (x, y), (w, h), wrap(node, 12), fc=colors[i % len(colors)], fs=9.2)
    for left, right in zip(boxes, boxes[1:]):
        arrow(ax, (left[0] + left[2] + 0.03, y + h / 2), (right[0] - 0.03, y + h / 2))
    box(ax, (1.45, 0.78), (7.1, 0.56), note, fc=GRAY, fs=9.0, lw=0.9)
    save(fig, name)


def trust_boundaries():
    flow_figure(
        "fig_trust-boundaries.png",
        "系统资产流转与主要信任边界",
        ["入口适配器\n外部消息", "安全壳入口\n会话/白名单", "Proxy /v1/scan\n输入扫描", "Agent Runtime\n工具门控", "OpenClaw/MCP\n工具输出"],
        "边界1：外部消息进入本机运行时；边界2：模型建议进入真实工具执行；边界3：工具结果回流上下文。",
        [RED, BLUE, GREEN, YELLOW, GRAY],
    )


def architecture():
    fig, ax = plt.subplots(figsize=(10.8, 5.7))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    title(ax, "Agent-Firewall 当前总体架构")
    box(ax, (0.42, 4.25), (2.15, 0.72), "消息入口适配器\nTelegram Bridge\n后续可扩展 CLI/Webhook", RED, 8.5)
    box(ax, (3.00, 4.25), (2.25, 0.72), "Nuxt/Vuetify 控制台\nAttack / Approvals\nSkills / Trace / Settings", BLUE, 8.5)
    box(ax, (7.35, 4.25), (2.15, 0.72), "回复通道\n原入口返回\n审批后续执行", GRAY, 8.5)
    box(ax, (1.20, 2.65), (2.65, 0.82), "Agent Runtime :8002\ngraph-compatible runner\npre/post tool gates", YELLOW, 8.7)
    box(ax, (5.95, 2.65), (2.65, 0.82), "Proxy Service :8000\n/v1/scan\n审计 / interventions\nOpenClaw 发现", GREEN, 8.7)
    box(ax, (1.20, 1.15), (2.65, 0.72), "本地状态\nSQLite + memory cache", GRAY, 9)
    box(ax, (5.95, 1.15), (2.65, 0.72), "OpenClaw/MCP Runtime\nskills / hooks / providers", PURPLE, 9)
    arrow(ax, (2.05, 4.25), (2.25, 3.47))
    arrow(ax, (3.85, 4.25), (3.20, 3.47))
    arrow(ax, (7.35, 4.25), (7.35, 3.47))
    arrow(ax, (3.85, 3.05), (5.95, 3.05))
    arrow(ax, (5.95, 2.90), (3.85, 2.90))
    arrow(ax, (3.82, 2.65), (5.98, 1.87), rad=-0.08)
    arrow(ax, (2.52, 2.65), (2.52, 1.87))
    arrow(ax, (7.28, 2.65), (7.28, 1.87))
    box(ax, (1.35, 0.28), (7.3, 0.45), "核心边界：Agent-Firewall 包裹 OpenClaw 工具执行；Telegram 只是当前入口适配器之一。", TEAL, 8.8)
    save(fig, "fig_architecture.png")


def proxy_pipeline():
    flow_figure(
        "fig_proxy-pipeline.png",
        "Proxy scan-only 检测流水线",
        ["parse\n消息规范化", "intent\n攻击意图分类", "rules\ndenylist/长度/编码", "scanners\n本地扫描", "decision\n风险聚合", "audit\n请求日志"],
        "输出语义：ALLOW 继续运行，MODIFY 清洗后继续，BLOCK 暂停或拒绝。",
        [BLUE, BLUE, GREEN, YELLOW, RED, GRAY],
    )


def agent_pipeline():
    fig, ax = plt.subplots(figsize=(11.2, 5.2))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 5.5)
    ax.axis("off")
    title(ax, "Agent Runtime 运行图与工具安全边界")
    nodes = [
        ("input\n会话/清洗", BLUE),
        ("intent\n意图记录", BLUE),
        ("policy\n角色工具", GREEN),
        ("router\n工具规划", YELLOW),
        ("pre-tool\nRBAC/Schema\n预算确认", RED),
        ("executor\nInternal/OpenClaw/MCP", ORANGE),
    ]
    boxes = []
    for i, (label, color) in enumerate(nodes):
        x = 0.35 + i * 1.72
        boxes.append((x, 3.35, 1.28, 0.76))
        box(ax, (x, 3.35), (1.28, 0.76), label, color, 8.0)
    for left, right in zip(boxes, boxes[1:]):
        arrow(ax, (left[0] + left[2], 3.73), (right[0], 3.73))
    box(ax, (8.95, 1.92), (1.45, 0.72), "post-tool\nPII/密钥\n注入清洗", PURPLE, 8.0)
    box(ax, (6.45, 1.92), (1.45, 0.72), "llm call\nProxy预扫\n模型响应", RED, 8.0)
    box(ax, (4.05, 1.92), (1.45, 0.72), "response\n最终回复", GRAY, 8.2)
    box(ax, (1.70, 1.92), (1.45, 0.72), "memory\n会话/Trace", GRAY, 8.2)
    arrow(ax, (9.60, 3.35), (9.60, 2.64))
    arrow(ax, (8.95, 2.28), (7.90, 2.28))
    arrow(ax, (6.45, 2.28), (5.50, 2.28))
    arrow(ax, (4.05, 2.28), (3.15, 2.28))
    box(ax, (4.32, 0.58), (2.35, 0.62), "INTERVENTION\n敏感工具或阻断输入进入审批队列", RED, 8.0)
    arrow(ax, (8.05, 3.35), (5.50, 1.20), color="#dc2626", rad=0.15)
    arrow(ax, (6.95, 1.92), (5.65, 1.20), color="#dc2626", rad=-0.15)
    save(fig, "fig_agent-pipeline.png")


def intervention_flow():
    flow_figure(
        "fig_intervention-flow.png",
        "Intervention 人工审批闭环",
        ["暂停触发\nBLOCK/确认", "创建审批项\npending", "控制台审核\napprove/reject", "Bridge worker\n审批后重放", "完成回复\nTrace更新"],
        "拒绝路径不会执行真实敏感工具；批准路径携带 approved_intervention_id 复核后继续。",
        [RED, YELLOW, BLUE, GREEN, GRAY],
    )


def risk_chart():
    labels = ["Intent", "Rules", "Scanners", "PII", "Secrets", "Boost"]
    values = [5, 4, 4, 3, 3, 2]
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    bars = ax.bar(labels, values, color="#93c5fd", edgecolor=LINE, linewidth=0.9)
    ax.set_ylabel("信号类别数量（归类）")
    ax.set_ylim(0, 5.8)
    ax.set_title("Proxy 风险聚合信号归类", loc="left", fontweight="bold")
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.08, str(val), ha="center", fontsize=9)
    save(fig, "fig_risk.png")


def delegation():
    flow_figure(
        "fig_delegation.png",
        "子 Agent 委派链的门控与审计",
        ["Main Agent\n入口任务", "Gate\n角色/参数/预算", "Subagent/Tool\nOpenClaw 或 MCP", "Trace\n委派证据链"],
        "委派被建模为受保护工具调用，避免低权限用户诱导高权限代理代办。",
        [BLUE, GREEN, YELLOW, GRAY],
    )


def trace_evidence():
    flow_figure(
        "fig_trace-evidence.png",
        "Trace 审计证据链",
        ["输入扫描\nrisk flags/decision", "工具计划\ntool name/args", "Pre gate\nRBAC/Schema/Confirm", "Tool exec\nprovider/latency", "Post gate\nredaction/block"],
        "每个跨边界动作都记录时间、原因、结果和脱敏预览。",
        [BLUE, GREEN, YELLOW, ORANGE, RED],
    )


def redteam_chart():
    groups, decisions = scenario_groups()
    top = sorted(groups, key=lambda x: x[1], reverse=True)[:12]
    labels = [g for g, _ in top][::-1]
    vals = [v for _, v in top][::-1]
    fig, ax = plt.subplots(figsize=(8.8, 6.2))
    bars = ax.barh(labels, vals, color="#bfdbfe", edgecolor=LINE, linewidth=0.8)
    ax.set_xlabel("场景数量")
    ax.set_title("当前红队资产中代表性类别样本数", loc="left", fontweight="bold")
    for bar, val in zip(bars, vals):
        ax.text(val + 0.5, bar.get_y() + bar.get_height() / 2, str(val), va="center", fontsize=8.5)
    max_val = max(vals)
    ax.set_xlim(0, max_val + 8)
    save(fig, "fig_redteam.png")

    # A compact expected-decision summary used by the same data pipeline.
    total_play = sum(decisions["playground"].values())
    total_agent = sum(decisions["agent"].values())
    assert total_play == 216 and total_agent == 142


def benchmark_compare():
    labels = ["轻量规则\n回归口径", "完整扫描器\n防护口径"]
    deterministic = [4, 4]
    semantic = [0, 3]
    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    x = np.arange(len(labels))
    ax.bar(x, deterministic, width=0.5, color="#93c5fd", edgecolor=LINE, label="确定性信号层")
    ax.bar(x, semantic, bottom=deterministic, width=0.5, color="#fed7aa", edgecolor=LINE, label="ML/实体扫描层")
    ax.set_xticks(x, labels)
    ax.set_ylabel("覆盖层数")
    ax.set_ylim(0, 8)
    ax.set_title("轻量规则口径与完整扫描器口径的覆盖层数对比", loc="left", fontweight="bold")
    ax.legend(frameon=False, loc="upper left")
    for idx, total in enumerate([sum(v) for v in zip(deterministic, semantic)]):
        ax.text(idx, total + 0.12, str(total), ha="center", fontsize=9)
    save(fig, "fig_benchmark-compare.png")


def latency():
    labels = ["parse", "intent", "rules", "scanners", "decision"]
    light = [1, 1, 1, 1, 1]
    full = [1, 1, 1, 4, 1]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    ax.bar(x - 0.18, light, width=0.36, color="#bfdbfe", edgecolor=LINE, label="轻量规则口径")
    ax.bar(x + 0.18, full, width=0.36, color="#fed7aa", edgecolor=LINE, label="完整扫描器口径")
    ax.set_xticks(x, labels)
    ax.set_ylabel("相对开销等级")
    ax.set_ylim(0, 5)
    ax.set_title("Pre-LLM 流水线相对开销分解", loc="left", fontweight="bold")
    ax.legend(frameon=False, loc="upper left")
    save(fig, "fig_latency.png")


def main() -> None:
    configure()
    trust_boundaries()
    architecture()
    proxy_pipeline()
    agent_pipeline()
    intervention_flow()
    risk_chart()
    delegation()
    trace_evidence()
    redteam_chart()
    benchmark_compare()
    latency()
    print(f"generated figures in {OUT}")


if __name__ == "__main__":
    main()
