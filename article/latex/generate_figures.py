#!/usr/bin/env python3
"""Generate reproducible quantitative/analytical figures for article.tex.

This script intentionally covers only figures whose values are derived from
repo-local scenario assets or from the fixed experimental scope described in
the paper. Architecture, flow, and schematic figures are handled by
article/generate_excalidraw_flowcharts.mjs.
"""

from __future__ import annotations

import json
import textwrap
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager

try:
    import scienceplots  # noqa: F401

    plt.style.use(["science", "no-latex", "grid"])
except Exception:
    plt.style.use("default")


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
OUT = ROOT / "figures"
SCENARIO_DIR = REPO_ROOT / "apps" / "proxy-service" / "data" / "scenarios"
OUT.mkdir(exist_ok=True)

INK = "#1f2937"
LINE = "#334155"
BLUE = "#2563eb"
LIGHT_BLUE = "#bfdbfe"
GREEN = "#16a34a"
LIGHT_GREEN = "#bbf7d0"
ORANGE = "#f97316"
LIGHT_ORANGE = "#fed7aa"
RED = "#dc2626"
LIGHT_RED = "#fecaca"
PURPLE = "#7c3aed"
LIGHT_PURPLE = "#ddd6fe"
GRAY = "#64748b"


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
    plt.rcParams.update(
        {
            "axes.unicode_minus": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "figure.dpi": 160,
            "savefig.dpi": 320,
            "axes.edgecolor": LINE,
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "text.color": INK,
            "axes.titleweight": "bold",
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 8.5,
            "legend.fontsize": 8.5,
        }
    )


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(OUT / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _scenario_counts() -> Counter[str]:
    counts: Counter[str] = Counter()
    for name in ("playground", "agent"):
        data = json.loads((SCENARIO_DIR / f"{name}.json").read_text(encoding="utf-8"))
        for group in data:
            counts[group["label"]] += len(group.get("items", []))
    return counts


def _wrap(label: str, width: int = 18) -> str:
    return "\n".join(textwrap.wrap(label, width=width, break_long_words=False))


def risk_signal_groups() -> None:
    labels = ["Intent", "Rules", "Scanners", "PII", "Secrets", "Boost"]
    values = [5, 4, 4, 3, 3, 2]
    colors = [LIGHT_BLUE, LIGHT_GREEN, LIGHT_ORANGE, LIGHT_PURPLE, LIGHT_RED, "#e2e8f0"]

    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    bars = ax.bar(labels, values, color=colors, edgecolor=LINE, linewidth=1.0)
    ax.set_ylim(0, 5.4)
    ax.set_ylabel("信号类别数量（归类）")
    ax.set_title("Proxy风险聚合信号归类")
    ax.grid(axis="y", alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.12, str(value), ha="center", fontsize=9)
    ax.text(
        0.0,
        -0.22,
        "说明：该图表示系统实现中的代表性信号子类数量，不表示实测拦截率或权重。",
        transform=ax.transAxes,
        ha="left",
        fontsize=8.5,
        color=GRAY,
    )
    save(fig, "fig_risk_scoring.pdf")


def redteam_categories() -> None:
    counts = _scenario_counts()
    selected = [
        ("Prompt Injection", counts["Prompt Injection"]),
        ("Jailbreak", counts["Jailbreak"]),
        ("PII/Sensitive", counts["PII / Sensitive Data"]),
        ("Obfuscation", counts["Obfuscation Attacks"]),
        ("Multi-Language", counts["Multi-Language Attacks"]),
        ("Tool Abuse", counts["Tool Abuse"]),
        ("Social Engineering", counts["Social Engineering"]),
        ("Data Exfiltration", counts["Data Exfiltration"]),
        ("RAG Poisoning", counts["RAG Poisoning"]),
        ("Confused Deputy", counts["Confused Deputy"]),
        ("Resource Exhaustion", counts["Resource Exhaustion"]),
    ]
    labels, values = zip(*selected)

    fig, ax = plt.subplots(figsize=(8.4, 6.4))
    y = list(range(len(labels)))
    bars = ax.barh(y, values, color=LIGHT_BLUE, edgecolor=LINE, linewidth=0.9)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 18)
    ax.set_xlabel("场景数量")
    ax.set_title("红队资产中代表性类别样本数")
    ax.grid(axis="x", alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    for bar, value in zip(bars, values):
        ax.text(value + 0.35, bar.get_y() + bar.get_height() / 2, str(value), va="center", fontsize=8.5)
    save(fig, "fig_redteam_categories.pdf")


def benchmark_compare() -> None:
    labels = ["轻量规则\n回归口径", "完整扫描器\n防护口径"]
    deterministic_layers = [4, 7]
    scanner_layers = [0, 3]
    x = [0, 1]

    fig, ax = plt.subplots(figsize=(7.4, 4.7))
    width = 0.35
    ax.bar([i - width / 2 for i in x], deterministic_layers, width, label="确定性信号层", color=LIGHT_BLUE, edgecolor=LINE)
    ax.bar([i + width / 2 for i in x], scanner_layers, width, label="ML/实体扫描层", color=LIGHT_ORANGE, edgecolor=LINE)
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 8.5)
    ax.set_ylabel("覆盖层数")
    ax.set_title("轻量规则口径与完整扫描器口径的能力分解")
    ax.legend(frameon=False, loc="upper left")
    ax.grid(axis="y", alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    for xpos, value in zip([i - width / 2 for i in x], deterministic_layers):
        ax.text(xpos, value + 0.15, str(value), ha="center", fontsize=8.5)
    for xpos, value in zip([i + width / 2 for i in x], scanner_layers):
        ax.text(xpos, value + 0.15, str(value), ha="center", fontsize=8.5)
    ax.text(
        0,
        -0.24,
        "说明：该图为能力分解，不作为外部benchmark或实测检出率。",
        transform=ax.transAxes,
        ha="left",
        fontsize=8.5,
        color=GRAY,
    )
    save(fig, "fig_benchmark_compare.pdf")


def latency_breakdown() -> None:
    nodes = ["parse", "intent", "rules", "scanners", "decision"]
    lightweight = [1, 1, 1, 1, 1]
    full = [1, 1, 1, 4, 1]
    x = list(range(len(nodes)))
    width = 0.36

    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    ax.bar([i - width / 2 for i in x], lightweight, width, label="轻量规则口径", color=LIGHT_BLUE, edgecolor=LINE)
    ax.bar([i + width / 2 for i in x], full, width, label="完整扫描器口径", color=LIGHT_ORANGE, edgecolor=LINE)
    ax.set_xticks(x, nodes)
    ax.set_ylim(0, 5)
    ax.set_ylabel("相对开销等级")
    ax.set_title("Pre-LLM流水线结构化相对开销分解")
    ax.legend(frameon=False, loc="upper left")
    ax.grid(axis="y", alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    for xpos, value in zip([i + width / 2 for i in x], full):
        ax.text(xpos, value + 0.12, str(value), ha="center", fontsize=8.5)
    ax.text(
        0,
        -0.24,
        "说明：该图表示结构化相对开销等级，不表示毫秒实测值。",
        transform=ax.transAxes,
        ha="left",
        fontsize=8.5,
        color=GRAY,
    )
    save(fig, "fig_latency_breakdown.pdf")


def main() -> None:
    configure_fonts()
    risk_signal_groups()
    redteam_categories()
    benchmark_compare()
    latency_breakdown()


if __name__ == "__main__":
    main()
