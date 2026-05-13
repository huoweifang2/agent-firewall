#!/usr/bin/env python3
"""Generate article data figures in a SciencePlots publication style."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

try:
    import scienceplots  # noqa: F401

    plt.style.use(["science", "no-latex", "grid"])
except Exception:
    plt.style.use("default")


ARTICLE_DIR = Path(__file__).resolve().parent
ROOT = ARTICLE_DIR.parent
OUT = ARTICLE_DIR / "images"
SCENARIOS = ROOT / "apps/proxy-service/data/scenarios"
YAML_PACKS = ROOT / "apps/proxy-service/src/proxy_service/domain/red_team/packs/data"

INK = "#172033"
MUTED = "#64748b"
BLUE = "#3b82f6"
GREEN = "#22c55e"
ORANGE = "#f97316"
RED = "#ef4444"
PURPLE = "#8b5cf6"
TEAL = "#14b8a6"
GRAY = "#94a3b8"


def configure() -> None:
    candidates = ["Songti SC", "PingFang SC", "Heiti SC", "Arial Unicode MS", "Noto Sans CJK SC"]
    available = {font.name for font in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = "sans-serif"
            plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            break
    plt.rcParams.update({
        "figure.dpi": 150,
        "savefig.dpi": 320,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "axes.unicode_minus": False,
        "axes.titlesize": 18,
        "axes.labelsize": 14,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
        "legend.fontsize": 12,
        "text.color": INK,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
    })


def save(fig: plt.Figure, slug: str) -> None:
    fig.tight_layout()
    fig.savefig(OUT / f"{slug}.png", bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / f"{slug}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def load_scenario_stats() -> tuple[Counter[str], Counter[str], dict[str, int]]:
    categories: Counter[str] = Counter()
    expected: Counter[str] = Counter()
    files: dict[str, int] = {}
    for filename in ["playground.json", "agent.json"]:
        data = json.loads((SCENARIOS / filename).read_text(encoding="utf-8"))
        total = 0
        for group in data:
            items = group.get("items", [])
            total += len(items)
            categories[group["label"]] += len(items)
            for item in items:
                expected[item.get("expectedDecision", "ALLOW")] += 1
        files[filename] = total
    return categories, expected, files


def yaml_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in sorted(YAML_PACKS.glob("*.yaml")):
        match = re.search(r"^scenario_count:\s*(\d+)", path.read_text(encoding="utf-8"), re.MULTILINE)
        if match:
            counts[path.stem] = int(match.group(1))
    return counts


def annotate_bars(ax: plt.Axes, bars, *, dy: float = 3, fmt: str = "{:.0f}") -> None:
    for bar in bars:
        value = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + dy,
            fmt.format(value),
            ha="center",
            va="bottom",
            fontsize=12,
            fontweight="bold",
            color=INK,
        )


def fig_5_1_dataset_inventory() -> None:
    _, expected, files = load_scenario_stats()
    yaml_total = sum(yaml_counts().values())
    fig, axes = plt.subplots(1, 2, figsize=(13.8, 5.4), gridspec_kw={"width_ratios": [1.15, 1]})
    fig.suptitle("实验数据与证据口径", fontsize=20, fontweight="bold", x=0.03, ha="left")

    labels = ["playground\nJSON", "agent\nJSON", "YAML\n场景资产", "public mapped\n新增映射", "Agent gate\n单元测试", "链路回放"]
    values = [files["playground.json"], files["agent.json"], yaml_total, 40, 125, 11]
    colors = [BLUE, GREEN, ORANGE, PURPLE, TEAL, GRAY]
    ax = axes[0]
    bars = ax.bar(labels, values, color=colors, alpha=0.82, edgecolor=INK, linewidth=0.8)
    annotate_bars(ax, bars, dy=5)
    ax.set_ylabel("场景 / 测试数量")
    ax.set_ylim(0, max(values) + 55)
    ax.set_title("数据来源规模", fontweight="bold")
    ax.text(2, yaml_total + 24, "147 = 107 原有 + 40 新增", ha="center", color=MUTED, fontsize=11)
    ax.tick_params(axis="x", rotation=0)

    ax = axes[1]
    pie_values = [expected["BLOCK"], expected["MODIFY"], expected["ALLOW"]]
    pie_labels = ["BLOCK", "MODIFY", "ALLOW"]
    wedges, texts, autotexts = ax.pie(
        pie_values,
        labels=pie_labels,
        autopct=lambda pct: f"{pct:.1f}%",
        startangle=0,
        colors=["#fecaca", "#fde68a", "#bbf7d0"],
        wedgeprops={"edgecolor": INK, "linewidth": 1.0},
        textprops={"fontsize": 13, "fontweight": "bold", "color": INK},
    )
    ax.set_title("358 个主实验样本预期决策", fontweight="bold")
    ax.text(0, -1.25, "322 BLOCK / 16 MODIFY / 20 ALLOW", ha="center", fontsize=13, color=MUTED)
    save(fig, "fig_5_1_dataset_inventory")


def fig_5_2_category_distribution() -> None:
    categories, _, _ = load_scenario_stats()
    selected = [
        "Safe (ALLOW)", "Jailbreak", "Prompt Injection", "Excessive Agency",
        "PII / Sensitive Data", "Obfuscation Attacks", "Toxicity & Harmful",
        "Secrets Detection", "Multi-Language Attacks", "Tool Abuse",
        "Prompt Injection (Agent)", "RAG Poisoning",
    ]
    labels = selected[::-1]
    values = [categories[x] for x in selected][::-1]
    fig, ax = plt.subplots(figsize=(10.8, 7.0))
    bars = ax.barh(labels, values, color="#bfdbfe", edgecolor=INK, linewidth=0.8)
    ax.set_title("主实验代表性类别样本分布", loc="left", fontweight="bold")
    ax.set_xlabel("场景数量")
    ax.set_xlim(0, max(values) + 4)
    for bar, value in zip(bars, values):
        ax.text(value + 0.25, bar.get_y() + bar.get_height() / 2, str(value), va="center", fontsize=12, fontweight="bold")
    save(fig, "fig_5_2_category_distribution")


def fig_5_3_baseline_comparison() -> None:
    labels = ["未保护直连\nLLM", "fast\nrules-only", "balanced\n默认策略"]
    correct = np.array([20, 269, 274])
    total = 358
    missed = total - correct
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(9.6, 5.8))
    ax.bar(x, correct, color=[GRAY, BLUE, GREEN], alpha=0.84, edgecolor=INK, linewidth=0.9, label="符合预期")
    ax.bar(x, missed, bottom=correct, color="#e5e7eb", edgecolor=INK, linewidth=0.6, label="未符合预期")
    ax.set_title("Baseline 与默认策略安全边界对比", loc="left", fontweight="bold")
    ax.set_ylabel("场景数 / 358")
    ax.set_ylim(0, 390)
    ax.set_xticks(x, labels)
    ax.legend(frameon=False, loc="upper left")
    for i, value in enumerate(correct):
        ax.text(i, value + 8, f"{value}/358", ha="center", fontsize=13, fontweight="bold")
    ax.text(2, 34, "84 漏报", ha="center", fontsize=12, color=RED, fontweight="bold")
    save(fig, "fig_5_3_baseline_comparison")


def fig_5_4_failure_distribution() -> None:
    labels = [
        "Secrets Detection", "Obfuscation Attacks", "Multi-Language Attacks",
        "Obfuscation (Agent)", "Multi-Language (Agent)", "RAG Poisoning",
        "Adversarial Suffixes", "Payload Splitting", "Social Engineering",
        "Multi-Turn Escalation",
    ]
    fast = np.array([10, 11, 10, 6, 5, 4, 5, 4, 3, 3])
    balanced = np.array([10, 10, 9, 6, 5, 4, 4, 4, 3, 3])
    y = np.arange(len(labels))[::-1]
    fig, ax = plt.subplots(figsize=(10.8, 7.0))
    ax.barh(y + 0.18, fast, height=0.34, color="#93c5fd", edgecolor=INK, linewidth=0.7, label="fast 漏报")
    ax.barh(y - 0.18, balanced, height=0.34, color="#fecaca", edgecolor=INK, linewidth=0.7, label="balanced 漏报")
    ax.set_yticks(y, labels)
    ax.set_xlabel("漏报数")
    ax.set_xlim(0, 13)
    ax.set_title("balanced 84 个漏报的主要类别分布", loc="left", fontweight="bold")
    ax.legend(frameon=False, loc="lower right")
    for yy, value in zip(y - 0.18, balanced):
        ax.text(value + 0.16, yy, str(value), va="center", fontsize=11, fontweight="bold")
    ax.text(0, -1.1, "来源：本轮 baseline 复算；balanced 漏报总数为 84，其中 playground=50、agent=34。", fontsize=11, color=MUTED)
    save(fig, "fig_5_4_failure_distribution")


def fig_5_5_chain_replay_matrix() -> None:
    rows = [f"CHAIN-{i:02d}" for i in range(1, 12)]
    cols = ["RBAC", "参数", "上下文", "确认", "执行", "清洗", "Trace"]
    matrix = np.array([
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
    ])
    fig, ax = plt.subplots(figsize=(9.4, 7.2))
    ax.imshow(matrix, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(cols)), cols)
    ax.set_yticks(np.arange(len(rows)), rows)
    ax.tick_params(top=True, bottom=False, labeltop=True, labelbottom=False)
    ax.set_title("Agent 工具链离线回放覆盖矩阵（11/11 passed）", loc="left", fontweight="bold")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            if matrix[i, j]:
                ax.scatter(j, i, s=52, color="white", edgecolor=INK, linewidth=0.35, zorder=3)
    ax.set_xticks(np.arange(-.5, len(cols), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(rows), 1), minor=True)
    ax.grid(which="minor", color="white", linestyle="-", linewidth=1.5)
    save(fig, "fig_5_5_chain_replay_matrix")


def fig_5_6_openclaw_rerun() -> None:
    labels = ["OC-01\nHTTP safe", "OC-02\nHTTP block", "TG-01\nTelegram safe", "TG-02\nTelegram block", "TG-03\nIndirect"]
    latency = [10279, 66, 8698, 47, 1546]
    colors = [GREEN, RED, GREEN, RED, ORANGE]
    fig, ax = plt.subplots(figsize=(10.2, 5.8))
    bars = ax.bar(labels, latency, color=colors, alpha=0.82, edgecolor=INK, linewidth=0.8)
    ax.set_title("OpenClaw / Telegram 真实链路复测耗时", loc="left", fontweight="bold")
    ax.set_ylabel("总耗时 ms")
    ax.set_ylim(0, 11500)
    annotate_bars(ax, bars, dy=140)
    ax.text(0.5, 10800, "OC/TG 安全请求均执行 openclaw_summarize；阻断请求无工具执行", color=MUTED, fontsize=11)
    save(fig, "fig_5_6_openclaw_rerun")


def main() -> None:
    configure()
    OUT.mkdir(parents=True, exist_ok=True)
    for fn in [
        fig_5_1_dataset_inventory,
        fig_5_2_category_distribution,
        fig_5_3_baseline_comparison,
        fig_5_4_failure_distribution,
        fig_5_5_chain_replay_matrix,
        fig_5_6_openclaw_rerun,
    ]:
        fn()
        print(f"generated {fn.__name__}")


if __name__ == "__main__":
    main()
