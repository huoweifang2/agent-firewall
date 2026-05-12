#!/usr/bin/env python3
"""Generate thesis figures for article.md.

The figures are deterministic and use only repository-local scenario files,
paper constants, and already recorded experiment results.  The script does not
reuse DOCX/LaTeX figure assets and does not call AutoFigure.
"""

from __future__ import annotations

import json
import math
import re
import textwrap
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

try:
    import scienceplots  # noqa: F401

    plt.style.use(["science", "no-latex", "grid"])
except Exception:
    plt.style.use("default")


ARTICLE_DIR = Path(__file__).resolve().parent
REPO_ROOT = ARTICLE_DIR.parent
OUT = ARTICLE_DIR / "images"
SCENARIO_DIR = REPO_ROOT / "apps" / "proxy-service" / "data" / "scenarios"
YAML_DIR = REPO_ROOT / "apps" / "proxy-service" / "src" / "red_team" / "packs" / "data"
OUT.mkdir(parents=True, exist_ok=True)

INK = "#1f2937"
MUTED = "#64748b"
LINE = "#334155"
BLUE = "#dbeafe"
BLUE_D = "#2563eb"
GREEN = "#dcfce7"
GREEN_D = "#16a34a"
YELLOW = "#fef3c7"
YELLOW_D = "#ca8a04"
RED = "#fee2e2"
RED_D = "#dc2626"
PURPLE = "#ede9fe"
PURPLE_D = "#7c3aed"
ORANGE = "#ffedd5"
ORANGE_D = "#f97316"
TEAL = "#ccfbf1"
GRAY = "#f1f5f9"
WHITE = "#ffffff"
PALETTE = [BLUE, GREEN, YELLOW, RED, PURPLE, ORANGE, TEAL, GRAY]


def configure() -> None:
    candidates = [
        "Songti SC",
        "PingFang SC",
        "Heiti SC",
        "Arial Unicode MS",
        "Noto Sans CJK SC",
        "SimSong",
    ]
    available = {font.name for font in font_manager.fontManager.ttflist}
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
            "axes.titleweight": "bold",
            "axes.titlesize": 12.5,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
        }
    )


def wrap(text: str, width: int = 13) -> str:
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False))


def save(fig: plt.Figure, slug: str) -> None:
    png = OUT / f"{slug}.png"
    pdf = OUT / f"{slug}.pdf"
    fig.savefig(png, bbox_inches="tight", facecolor=WHITE)
    fig.savefig(pdf, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)


def title(ax: plt.Axes, text: str) -> None:
    ax.text(0.02, 0.965, text, transform=ax.transAxes, fontsize=13.2, fontweight="bold", va="top")


def note(ax: plt.Axes, text: str, y: float = 0.045) -> None:
    ax.text(0.02, y, text, transform=ax.transAxes, fontsize=8.2, color=MUTED, va="bottom")


def box(
    ax: plt.Axes,
    xy: tuple[float, float],
    wh: tuple[float, float],
    text: str,
    *,
    fc: str = GRAY,
    ec: str = LINE,
    fs: float = 9,
    lw: float = 1.0,
    radius: float = 0.045,
) -> FancyBboxPatch:
    x, y = xy
    w, h = wh
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.025,rounding_size={radius}",
        fc=fc,
        ec=ec,
        lw=lw,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, linespacing=1.25)
    return patch


def arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = LINE,
    lw: float = 1.15,
    rad: float = 0,
    style: str = "-|>",
) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle=style,
            mutation_scale=12,
            lw=lw,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
        )
    )


def blank_canvas(width: float = 10.8, height: float = 5.8) -> tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    return fig, ax


def scenario_groups() -> tuple[Counter[str], Counter[str], dict[str, Counter[str]]]:
    category_counts: Counter[str] = Counter()
    expected_counts: Counter[str] = Counter()
    file_expected: dict[str, Counter[str]] = {}
    for filename in ("playground.json", "agent.json"):
        path = SCENARIO_DIR / filename
        data = json.loads(path.read_text(encoding="utf-8"))
        file_counter: Counter[str] = Counter()
        for group in data:
            items = group.get("items", [])
            category_counts[group["label"]] += len(items)
            for item in items:
                decision = item.get("expectedDecision", "ALLOW")
                expected_counts[decision] += 1
                file_counter[decision] += 1
        file_expected[filename] = file_counter
    return category_counts, expected_counts, file_expected


def yaml_pack_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in sorted(YAML_DIR.glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^scenario_count:\s*(\d+)\s*$", text, re.MULTILINE)
        if match:
            counts[path.stem] = int(match.group(1))
    return counts


def fig_2_1_trust_boundaries() -> None:
    fig, ax = blank_canvas(10.8, 5.6)
    title(ax, "系统资产流转与主要信任边界")

    nodes = [
        ("外部消息入口\nTelegram / 后续入口", RED),
        ("Agent Runtime\n/agent/chat", BLUE),
        ("Proxy /v1/scan\n输入扫描", GREEN),
        ("LLM 工具规划\nDeepSeek", YELLOW),
        ("pre-tool gate\n执行前门控", RED),
        ("OpenClaw/MCP\n工具输出", PURPLE),
        ("post-tool gate\n输出清洗", ORANGE),
        ("Trace / Audit\n证据落盘", GRAY),
    ]
    coords = [
        (0.35, 3.4),
        (2.0, 3.4),
        (3.65, 3.4),
        (5.3, 3.4),
        (6.95, 3.4),
        (6.95, 1.85),
        (5.3, 1.85),
        (3.65, 1.85),
    ]
    for (label, color), (x, y) in zip(nodes, coords):
        box(ax, (x, y), (1.28, 0.68), label, fc=color, fs=7.8)
    for a, b in zip(coords[:5], coords[1:5]):
        arrow(ax, (a[0] + 1.28, a[1] + 0.34), (b[0], b[1] + 0.34))
    arrow(ax, (7.59, 3.4), (7.59, 2.53))
    arrow(ax, (6.95, 2.19), (6.58, 2.19))
    arrow(ax, (5.3, 2.19), (4.93, 2.19))
    for x, label in [(2.62, "边界1\n入口不可信"), (6.3, "边界2\n计划不可信"), (6.3, "边界3\n结果不可信")]:
        y = 4.43 if "入口" in label else 2.78 if "计划" in label else 1.08
        box(ax, (x, y), (1.18, 0.42), label, fc=WHITE, ec=RED_D, fs=7.5, lw=1.0)
    arrow(ax, (4.29, 3.4), (4.29, 2.53), color=MUTED, style="->")
    note(ax, "说明：外部消息、模型工具计划、工具返回内容分别在进入下一边界前接受确定性检查。")
    save(fig, "fig_2_1_trust_boundaries")


def fig_3_1_architecture() -> None:
    fig, ax = blank_canvas(11.2, 6.1)
    title(ax, "Agent-Firewall 总体架构")
    box(ax, (0.45, 3.75), (1.65, 0.62), "消息入口适配器\nTelegram Bridge", fc=RED, fs=8.0)
    box(ax, (4.05, 4.05), (2.0, 0.62), "Frontend :3000\nAttack / Approvals\nTrace / Settings", fc=BLUE, fs=7.8)
    box(ax, (1.15, 2.45), (2.35, 0.8), "Agent Runtime :8002\n运行图 / LLM 调用\npre/post gate", fc=YELLOW, fs=8.2)
    box(ax, (5.85, 2.45), (2.35, 0.8), "Proxy Service :8000\n/v1/scan / 审批\nControl Plane", fc=GREEN, fs=8.2)
    box(ax, (1.15, 1.05), (2.35, 0.68), "SQLite + Memory\nTrace / Audit / Intervention", fc=GRAY, fs=8.0)
    box(ax, (5.85, 1.05), (2.35, 0.68), "OpenClaw / MCP\nskills / hooks / provider", fc=PURPLE, fs=8.0)
    box(ax, (8.55, 3.75), (1.05, 0.62), "回复通道", fc=GRAY, fs=8.0)

    arrow(ax, (2.1, 3.75), (2.3, 3.25))
    arrow(ax, (3.5, 2.86), (5.85, 2.86))
    arrow(ax, (5.85, 2.67), (3.5, 2.67))
    arrow(ax, (3.5, 2.45), (5.85, 1.68), rad=-0.08)
    arrow(ax, (2.32, 2.45), (2.32, 1.73))
    arrow(ax, (7.03, 2.45), (7.03, 1.73))
    arrow(ax, (8.2, 2.86), (8.9, 3.75), rad=0.06)
    arrow(ax, (4.85, 4.05), (6.2, 3.25), rad=-0.08)
    arrow(ax, (4.65, 4.05), (3.25, 3.25), rad=0.08)
    box(ax, (2.0, 0.22), (6.0, 0.42), "核心边界：消息入口只负责接入；工具执行由 Agent-Firewall 安全壳统一控制。", fc=TEAL, fs=8.3)
    save(fig, "fig_3_1_architecture")


def fig_4_1_method_overview() -> None:
    fig, ax = blank_canvas(11.8, 6.2)
    title(ax, "方法总览与工具调用安全状态流")
    steps = [
        ("用户消息", BLUE),
        ("输入解析\n会话加载", BLUE),
        ("Proxy /v1/scan", GREEN),
        ("LLM 回复\n或工具计划", YELLOW),
        ("pre-tool gate", RED),
        ("Provider\nOpenClaw/MCP/Internal", PURPLE),
        ("post-tool gate", ORANGE),
        ("最终回复", GRAY),
    ]
    xs = [0.25, 1.45, 2.9, 4.25, 5.65, 7.05, 8.45, 9.65]
    y = 3.0
    for (label, color), x in zip(steps, xs):
        box(ax, (x, y), (1.05, 0.66), label, fc=color, fs=7.5)
    for x1, x2 in zip(xs, xs[1:]):
        arrow(ax, (x1 + 1.05, y + 0.33), (x2, y + 0.33))
    box(ax, (2.75, 4.05), (1.25, 0.48), "BLOCK\ninput_block", fc=RED, fs=7.3)
    arrow(ax, (3.42, 3.66), (3.35, 4.05), color=RED_D)
    box(ax, (5.2, 4.05), (1.65, 0.48), "BLOCK / CONFIRM\nintervention", fc=RED, fs=7.3)
    arrow(ax, (6.17, 3.66), (6.02, 4.05), color=RED_D)
    box(ax, (8.35, 1.85), (1.5, 0.48), "BLOCK\n占位符入上下文", fc=RED, fs=7.3)
    arrow(ax, (8.98, 3.0), (9.1, 2.33), color=RED_D)
    box(ax, (3.85, 1.0), (3.0, 0.5), "Trace / Audit：记录输入扫描、工具计划、门控、执行、清洗和最终回复", fc=TEAL, fs=8.2)
    for x in [2.9, 5.65, 7.05, 8.45]:
        arrow(ax, (x + 0.53, y), (5.35, 1.5), color=MUTED, lw=0.85, rad=0.12, style="->")
    save(fig, "fig_4_1_method_overview")


def fig_4_2_scan_pipeline() -> None:
    fig, ax = blank_canvas(11, 5.2)
    title(ax, "/v1/scan scan-only 检测流水线")
    nodes = [
        ("parse\n消息规范化", BLUE),
        ("intent\n意图分类", BLUE),
        ("rules\ndenylist/编码/长度", GREEN),
        ("scanners\nLLM Guard / NeMo", YELLOW),
        ("decision\n风险聚合", RED),
        ("audit\n请求审计", GRAY),
    ]
    xs = np.linspace(0.55, 8.35, len(nodes))
    for (label, color), x in zip(nodes, xs):
        box(ax, (float(x), 2.8), (1.15, 0.72), label, fc=color, fs=7.8)
    for x1, x2 in zip(xs, xs[1:]):
        arrow(ax, (float(x1) + 1.15, 3.16), (float(x2), 3.16))
    for i, (decision, color, x) in enumerate([("ALLOW\n200", GREEN, 2.65), ("MODIFY\n200", YELLOW, 4.35), ("BLOCK\n403", RED, 6.05)]):
        box(ax, (x, 1.22), (1.15, 0.55), decision, fc=color, fs=8.0)
        arrow(ax, (6.1, 2.8), (x + 0.58, 1.77), color=MUTED, rad=(i - 1) * 0.08)
    note(ax, "说明：该接口不调用 LLM，只返回安全决策、风险分数、风险标记和阻断原因。")
    save(fig, "fig_4_2_scan_pipeline")


def fig_4_3_risk_decision() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.8), gridspec_kw={"width_ratios": [1.05, 1]})
    fig.suptitle("风险聚合与决策规则", fontsize=13.2, fontweight="bold", x=0.08, ha="left")
    labels = ["Intent", "Rules", "Scanners", "PII", "Secrets", "Boost"]
    values = [5, 4, 4, 3, 3, 2]
    colors = [BLUE_D, GREEN_D, ORANGE_D, PURPLE_D, RED_D, MUTED]
    ax = axes[0]
    bars = ax.bar(labels, values, color=colors, alpha=0.75, edgecolor=LINE, linewidth=0.8)
    ax.set_ylabel("代表性子类数量")
    ax.set_ylim(0, 5.8)
    ax.set_title("风险信号归类")
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.1, str(v), ha="center", fontsize=8.5)

    ax = axes[1]
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    rules = [
        ("denylist_hit", "BLOCK", RED),
        ("risk_score >= max_risk", "BLOCK", RED),
        ("pii_action = mask", "MODIFY", YELLOW),
        ("suspicious_intent", "BLOCK", RED),
        ("无高风险信号", "ALLOW", GREEN),
    ]
    for i, (cond, decision, color) in enumerate(rules):
        y = 4.1 - i * 0.78
        box(ax, (0.55, y), (3.3, 0.48), cond, fc=GRAY, fs=8.2)
        arrow(ax, (3.85, y + 0.24), (5.0, y + 0.24))
        box(ax, (5.0, y), (1.55, 0.48), decision, fc=color, fs=8.2)
    ax.text(0.55, 0.18, "说明：NeMo 等语义信号参与风险分数，不单独硬阻断。", fontsize=8.2, color=MUTED)
    save(fig, "fig_4_3_risk_decision")


def fig_4_4_agent_runtime_graph() -> None:
    fig, ax = blank_canvas(11.8, 5.7)
    title(ax, "Agent Runtime 运行图")
    top = [("input", BLUE), ("intent", BLUE), ("policy", GREEN), ("tool_router", YELLOW), ("llm_call", RED)]
    xs = [0.45, 1.75, 3.05, 4.35, 5.85]
    for (label, color), x in zip(top, xs):
        box(ax, (x, 3.55), (1.0, 0.58), label, fc=color, fs=8.0)
    for x1, x2 in zip(xs, xs[1:]):
        arrow(ax, (x1 + 1.0, 3.84), (x2, 3.84))
    loop = [
        ("tool_plan", YELLOW, 7.15, 3.55),
        ("pre-tool gate", RED, 8.45, 3.55),
        ("tool_executor", PURPLE, 8.45, 2.25),
        ("post-tool gate", ORANGE, 7.15, 2.25),
    ]
    for label, color, x, y in loop:
        box(ax, (x, y), (1.08, 0.58), label, fc=color, fs=7.8)
    arrow(ax, (6.85, 3.84), (7.15, 3.84))
    arrow(ax, (8.23, 3.84), (8.45, 3.84))
    arrow(ax, (8.99, 3.55), (8.99, 2.83))
    arrow(ax, (8.45, 2.54), (8.23, 2.54))
    arrow(ax, (7.69, 2.83), (6.45, 3.55), rad=0.15)
    box(ax, (4.0, 1.05), (1.2, 0.58), "response", fc=GRAY, fs=8.0)
    box(ax, (5.75, 1.05), (1.2, 0.58), "memory", fc=GRAY, fs=8.0)
    arrow(ax, (6.35, 3.55), (4.6, 1.63), rad=0.12)
    arrow(ax, (5.2, 1.34), (5.75, 1.34))
    box(ax, (7.0, 0.75), (2.0, 0.46), "max_iterations = 3", fc=TEAL, fs=8.0)
    save(fig, "fig_4_4_agent_runtime_graph")


def fig_4_5_pre_tool_gate() -> None:
    fig, ax = blank_canvas(11.2, 5.6)
    title(ax, "pre-tool gate 检查链与决策")
    checks = [
        ("RBAC\n角色允许列表", BLUE),
        ("Schema\n参数/注入", GREEN),
        ("Context risk\n外泄/升级", YELLOW),
        ("Limits\n次数/预算", ORANGE),
        ("Confirmation\n高敏确认", RED),
    ]
    xs = [0.55, 2.15, 3.75, 5.35, 6.95]
    for (label, color), x in zip(checks, xs):
        box(ax, (x, 3.05), (1.25, 0.72), label, fc=color, fs=7.8)
    for x1, x2 in zip(xs, xs[1:]):
        arrow(ax, (x1 + 1.25, 3.41), (x2, 3.41))
    decisions = [
        ("ALLOW\n直接执行", GREEN, 1.0),
        ("MODIFY\n参数清洗后执行", YELLOW, 3.2),
        ("BLOCK\n真实工具不执行", RED, 5.4),
        ("REQUIRE_CONFIRMATION\n进入审批", RED, 7.6),
    ]
    for text, color, x in decisions:
        box(ax, (x, 1.25), (1.55, 0.68), text, fc=color, fs=7.6)
    for x in xs:
        arrow(ax, (x + 0.63, 3.05), (5.0, 1.93), color=MUTED, lw=0.8, rad=0.08)
    note(ax, "说明：BLOCK 与 REQUIRE_CONFIRMATION 均发生在真实工具执行前。")
    save(fig, "fig_4_5_pre_tool_gate")


def fig_4_6_post_tool_gate() -> None:
    fig, ax = blank_canvas(11.2, 5.4)
    title(ax, "post-tool gate 输出清洗流程")
    nodes = [
        ("工具原始输出", PURPLE),
        ("Injection scan\n间接注入", RED),
        ("PII scan\n邮箱/电话/卡号", BLUE),
        ("Secrets scan\n密钥/连接串", ORANGE),
        ("Size check\n截断", YELLOW),
        ("上下文安全结果", GREEN),
    ]
    xs = [0.4, 1.95, 3.5, 5.05, 6.6, 8.15]
    for (label, color), x in zip(nodes, xs):
        box(ax, (x, 3.0), (1.15, 0.72), label, fc=color, fs=7.6)
    for x1, x2 in zip(xs, xs[1:]):
        arrow(ax, (x1 + 1.15, 3.36), (x2, 3.36))
    outs = [("PASS", GREEN), ("REDACT", ORANGE), ("TRUNCATE", YELLOW), ("BLOCK\n阻断占位符", RED)]
    for i, (label, color) in enumerate(outs):
        box(ax, (1.45 + i * 2.0, 1.4), (1.28, 0.56), label, fc=color, fs=8.0)
    arrow(ax, (2.5, 3.0), (7.1, 1.96), color=RED_D, rad=-0.12)
    note(ax, "说明：工具执行成功不代表结果可进入上下文；工具输出仍需经过清洗或阻断。")
    save(fig, "fig_4_6_post_tool_gate")


def fig_4_7_openclaw_bridge() -> None:
    fig, ax = blank_canvas(11.4, 5.6)
    title(ax, "OpenClaw provider 受保护桥接")
    nodes = [
        ("runtime spec\nprovider_type=openclaw", BLUE),
        ("build_scoped_prompt\n限定 skill/args", GREEN),
        ("OpenClaw CLI\nagent --json", PURPLE),
        ("provider result\nstdout/json", YELLOW),
        ("post-tool gate\n清洗后回流", ORANGE),
    ]
    xs = [0.45, 2.25, 4.05, 5.85, 7.65]
    for (label, color), x in zip(nodes, xs):
        box(ax, (x, 3.0), (1.45, 0.74), label, fc=color, fs=7.5)
    for x1, x2 in zip(xs, xs[1:]):
        arrow(ax, (x1 + 1.45, 3.37), (x2, 3.37))
    box(ax, (2.0, 1.42), (2.0, 0.56), "session 派生\nagent-firewall-<hash>", fc=TEAL, fs=8.0)
    box(ax, (5.05, 1.42), (2.1, 0.56), "timeout=120s\n异常转工具错误/HTTP 502", fc=RED, fs=8.0)
    arrow(ax, (3.0, 1.98), (3.0, 3.0), color=MUTED)
    arrow(ax, (6.1, 1.98), (6.55, 3.0), color=MUTED)
    save(fig, "fig_4_7_openclaw_bridge")


def fig_4_8_intervention_state() -> None:
    fig, ax = blank_canvas(11.2, 5.4)
    title(ax, "intervention 审批状态机")
    states = [
        ("触发暂停\ninput/tool/confirm", RED),
        ("pending\n等待审批", YELLOW),
        ("approved\n允许重放", GREEN),
        ("completed\n执行完成", GRAY),
    ]
    xs = [0.6, 2.7, 4.8, 6.9]
    for (label, color), x in zip(states, xs):
        box(ax, (x, 3.0), (1.35, 0.66), label, fc=color, fs=8.0)
    for x1, x2 in zip(xs, xs[1:]):
        arrow(ax, (x1 + 1.35, 3.33), (x2, 3.33))
    box(ax, (4.8, 1.35), (1.35, 0.58), "rejected\n不重放", fc=RED, fs=8.0)
    arrow(ax, (3.38, 3.0), (5.48, 1.93), color=RED_D, rad=-0.12)
    box(ax, (7.9, 1.35), (1.35, 0.58), "failed\n执行失败", fc=RED, fs=8.0)
    arrow(ax, (6.15, 3.0), (8.58, 1.93), color=RED_D, rad=-0.1)
    note(ax, "说明：审批状态由 Proxy 持久化；重放请求必须携带 approved_intervention_id 复核。")
    save(fig, "fig_4_8_intervention_state")


def fig_4_9_trace_evidence() -> None:
    fig, ax = blank_canvas(11.8, 5.8)
    title(ax, "Trace 审计证据链结构")
    columns = [
        ("请求元数据\nsession/role/policy/model", BLUE),
        ("输入扫描\nintent/risk/decision", GREEN),
        ("工具计划\ntool/args", YELLOW),
        ("pre-tool\nchecks/reason", RED),
        ("tool exec\nprovider/latency", PURPLE),
        ("post-tool\npii/secrets/injection", ORANGE),
        ("最终回复\nerrors/counters", GRAY),
    ]
    xs = np.linspace(0.35, 8.95, len(columns))
    for (label, color), x in zip(columns, xs):
        box(ax, (float(x), 3.05), (1.15, 0.74), label, fc=color, fs=7.1)
    for x1, x2 in zip(xs, xs[1:]):
        arrow(ax, (float(x1) + 1.15, 3.42), (float(x2), 3.42))
    box(ax, (2.0, 1.3), (5.8, 0.58), "Trace-run 可回答：在哪一层拦截、是否执行真实工具、原始结果是否进入上下文", fc=TEAL, fs=8.3)
    for x in xs[1:6]:
        arrow(ax, (float(x) + 0.58, 3.05), (4.9, 1.88), color=MUTED, lw=0.8, rad=0.08)
    save(fig, "fig_4_9_trace_evidence")


def fig_5_1_dataset_inventory() -> None:
    category_counts, expected_counts, _ = scenario_groups()
    yaml_total = sum(yaml_pack_counts().values())
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.8), gridspec_kw={"width_ratios": [1, 1.1]})
    fig.suptitle("实验数据与证据口径", fontsize=13.2, fontweight="bold", x=0.08, ha="left")

    ax = axes[0]
    labels = ["playground\nJSON", "agent\nJSON", "YAML\nbenchmark", "compare\nJSON", "OpenClaw\n小样本"]
    vals = [216, 142, yaml_total, 5, 7]
    colors = [BLUE_D, GREEN_D, ORANGE_D, PURPLE_D, RED_D]
    bars = ax.bar(labels, vals, color=colors, alpha=0.75, edgecolor=LINE, linewidth=0.8)
    ax.set_ylabel("样本/场景数")
    ax.set_title("数据来源规模")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 6, str(v), ha="center", fontsize=8.5)
    ax.set_ylim(0, max(vals) + 55)

    ax = axes[1]
    labels = ["BLOCK", "MODIFY", "ALLOW"]
    vals = [expected_counts["BLOCK"], expected_counts["MODIFY"], expected_counts["ALLOW"]]
    wedges, texts, autotexts = ax.pie(
        vals,
        labels=labels,
        autopct=lambda pct: f"{pct:.1f}%",
        colors=[RED, YELLOW, GREEN],
        wedgeprops={"edgecolor": LINE, "linewidth": 0.8},
        textprops={"fontsize": 9},
    )
    ax.set_title("358 个主实验样本预期决策")
    ax.text(0, -1.25, "322 BLOCK / 16 MODIFY / 20 ALLOW", ha="center", fontsize=8.5, color=MUTED)
    save(fig, "fig_5_1_dataset_inventory")


def fig_5_2_category_distribution() -> None:
    counts, _, _ = scenario_groups()
    selected = [
        "Jailbreak",
        "Prompt Injection",
        "PII / Sensitive Data",
        "Obfuscation Attacks",
        "Multi-Language Attacks",
        "Secrets Detection",
        "Tool Abuse",
        "Social Engineering",
        "Prompt Injection (Agent)",
        "Data Exfiltration (Agent)",
        "Role Bypass / Escalation",
        "RAG Poisoning",
    ]
    labels = [s.replace(" / ", "/") for s in selected][::-1]
    vals = [counts[s] for s in selected][::-1]
    fig, ax = plt.subplots(figsize=(9.2, 6.2))
    bars = ax.barh(labels, vals, color="#bfdbfe", edgecolor=LINE, linewidth=0.8)
    ax.set_xlabel("场景数量")
    ax.set_title("主实验代表性类别样本分布", loc="left", fontweight="bold")
    ax.set_xlim(0, max(vals) + 4)
    for b, v in zip(bars, vals):
        ax.text(v + 0.25, b.get_y() + b.get_height() / 2, str(v), va="center", fontsize=8.5)
    save(fig, "fig_5_2_category_distribution")


def fig_5_3_baseline_comparison() -> None:
    labels = ["直连 LLM", "fast", "balanced"]
    correct = np.array([20, 269, 274])
    missed = 358 - correct
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    x = np.arange(len(labels))
    ax.bar(x, correct, color=[MUTED, BLUE_D, GREEN_D], alpha=0.75, edgecolor=LINE, label="符合预期")
    ax.bar(x, missed, bottom=correct, color="#e5e7eb", edgecolor=LINE, label="未符合预期")
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 390)
    ax.set_ylabel("场景数 / 358")
    ax.set_title("Baseline 与默认策略安全边界对比", loc="left", fontweight="bold")
    ax.legend(frameon=False, loc="upper left")
    for i, v in enumerate(correct):
        ax.text(i, v + 8, f"{v}/358", ha="center", fontsize=9, fontweight="bold")
    save(fig, "fig_5_3_baseline_comparison")


def fig_5_4_failure_distribution() -> None:
    labels = [
        "Secrets Detection",
        "Obfuscation Attacks",
        "Multi-Language Attacks",
        "Obfuscation (Agent)",
        "Multi-Language (Agent)",
        "RAG Poisoning",
        "Adversarial Suffixes",
        "Payload Splitting",
        "Social Engineering",
        "Multi-Turn Escalation",
    ]
    fast = np.array([10, 11, 10, 6, 5, 4, 5, 4, 3, 3])
    balanced = np.array([10, 10, 9, 6, 5, 4, 4, 4, 3, 3])
    y = np.arange(len(labels))[::-1]
    fig, ax = plt.subplots(figsize=(9.4, 6.2))
    ax.barh(y + 0.18, fast, height=0.34, color="#bfdbfe", edgecolor=LINE, label="fast 漏报")
    ax.barh(y - 0.18, balanced, height=0.34, color="#fecaca", edgecolor=LINE, label="balanced 漏报")
    ax.set_yticks(y, labels)
    ax.set_xlabel("漏报数")
    ax.set_title("balanced 84 个漏报的主要类别分布", loc="left", fontweight="bold")
    ax.set_xlim(0, 13)
    ax.legend(frameon=False, loc="lower right")
    for yy, v in zip(y - 0.18, balanced):
        ax.text(v + 0.15, yy, str(v), va="center", fontsize=8.3)
    ax.text(0, -1.15, "来源：baseline 复算；balanced 漏报总数为 84，其中 playground=50、agent=34。", fontsize=8.2, color=MUTED)
    save(fig, "fig_5_4_failure_distribution")


def fig_5_5_chain_replay_matrix() -> None:
    rows = [f"CHAIN-{i:02d}" for i in range(1, 12)]
    cols = ["RBAC", "参数", "上下文", "确认", "执行", "清洗", "Trace"]
    matrix = np.array(
        [
            [1, 1, 0, 0, 1, 0, 1],
            [1, 0, 0, 0, 1, 0, 1],
            [0, 1, 0, 0, 0, 0, 1],
            [0, 0, 1, 0, 0, 0, 1],
            [0, 0, 1, 0, 0, 0, 1],
            [0, 0, 0, 1, 0, 0, 1],
            [0, 0, 0, 1, 1, 1, 1],
            [0, 0, 0, 0, 1, 1, 1],
            [0, 0, 0, 0, 1, 1, 1],
            [0, 1, 0, 0, 1, 0, 1],
            [0, 0, 0, 0, 1, 1, 1],
        ]
    )
    fig, ax = plt.subplots(figsize=(8.8, 6.4))
    im = ax.imshow(matrix, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(np.arange(len(cols)), cols)
    ax.set_yticks(np.arange(len(rows)), rows)
    ax.set_title("Agent 工具链离线回放覆盖矩阵（11/11 passed）", loc="left", fontweight="bold")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            if matrix[i, j]:
                ax.scatter(j, i, s=90, marker="s", color=BLUE_D, edgecolors=LINE, linewidths=0.4)
    ax.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False)
    ax.set_xlabel("")
    ax.set_ylabel("")
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02, ticks=[0, 1], label="覆盖")
    save(fig, "fig_5_5_chain_replay_matrix")


def fig_5_6_openclaw_rerun() -> None:
    fig, ax = blank_canvas(11.6, 5.8)
    title(ax, "本机 OpenClaw 复测链路与 7 个案例结果")
    flow = [
        ("health/status\n8000/8002", BLUE),
        ("active agent\nUUID", GREEN),
        ("/agent/chat\n受保护入口", YELLOW),
        ("openclaw_summarize\nprovider", PURPLE),
        ("Trace-run\n证据链", ORANGE),
    ]
    xs = [0.45, 2.2, 3.95, 5.7, 7.45]
    for (label, color), x in zip(flow, xs):
        box(ax, (x, 3.35), (1.35, 0.66), label, fc=color, fs=7.5)
    for x1, x2 in zip(xs, xs[1:]):
        arrow(ax, (x1 + 1.35, 3.68), (x2, 3.68))
    cases = [
        ("OC-01", "ALLOW\n工具调用", GREEN),
        ("OC-02", "BLOCK\n密钥泄露", RED),
        ("OC-03", "BLOCK\n内部工具", RED),
        ("OC-04", "DIRECT\n对照绕过", GRAY),
        ("OC-05", "SCAN BLOCK\nPII", RED),
        ("OC-06", "BLOCK\n间接注入", RED),
        ("OC-07", "ALLOW\noperator", GREEN),
    ]
    for i, (cid, result, color) in enumerate(cases):
        x = 0.55 + (i % 4) * 2.2
        y = 1.95 if i < 4 else 1.05
        box(ax, (x, y), (1.55, 0.58), f"{cid}\n{result}", fc=color, fs=7.3)
    note(ax, "说明：OpenClaw 小样本用于证明本机 provider 闭环，不并入 358 场景 baseline 分母。")
    save(fig, "fig_5_6_openclaw_rerun")


def main() -> None:
    configure()
    figures = [
        fig_2_1_trust_boundaries,
        fig_3_1_architecture,
        fig_4_1_method_overview,
        fig_4_2_scan_pipeline,
        fig_4_3_risk_decision,
        fig_4_4_agent_runtime_graph,
        fig_4_5_pre_tool_gate,
        fig_4_6_post_tool_gate,
        fig_4_7_openclaw_bridge,
        fig_4_8_intervention_state,
        fig_4_9_trace_evidence,
        fig_5_1_dataset_inventory,
        fig_5_2_category_distribution,
        fig_5_3_baseline_comparison,
        fig_5_4_failure_distribution,
        fig_5_5_chain_replay_matrix,
        fig_5_6_openclaw_rerun,
    ]
    for fn in figures:
        fn()
    print(f"generated {len(figures)} figures in {OUT}")


if __name__ == "__main__":
    main()
