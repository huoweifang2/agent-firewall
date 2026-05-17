#!/usr/bin/env python3
"""Generate article data figures with a unified SciPlotly-style theme.

The requested ``sciplotly`` package is not published on PyPI/npm in this
environment, so this script uses Plotly + Kaleido with a small local
publication theme: Songti font, fixed canvas sizes, shared margins, grid,
line widths, and a restrained color palette.
"""

from __future__ import annotations

import json
import re
import textwrap
from collections import Counter
from pathlib import Path
from typing import Iterable, Sequence

import plotly.graph_objects as go
from plotly.subplots import make_subplots


ARTICLE_DIR = Path(__file__).resolve().parent
ROOT = ARTICLE_DIR.parent
OUT = ARTICLE_DIR / "images"
SCENARIOS = ROOT / "apps/proxy-service/data/scenarios"
YAML_PACKS = ROOT / "apps/proxy-service/src/proxy_service/domain/red_team/packs/data"

WIDTH = 1600
HEIGHT = 1000
SCALE = 2

FONT = "Songti SC, SimSong, LiSong Pro, Arial Unicode MS, serif"
INK = "#1f2937"
MUTED = "#64748b"
GRID = "#e2e8f0"
AXIS = "#334155"
PAPER = "#ffffff"
PLOT = "#fbfdff"

BLUE = "#2563eb"
SKY = "#38bdf8"
GREEN = "#16a34a"
AMBER = "#d97706"
RED = "#dc2626"
PURPLE = "#7c3aed"
TEAL = "#0d9488"
GRAY = "#94a3b8"
SLATE = "#475569"
LIGHT = "#e5e7eb"

PALETTE = [BLUE, GREEN, AMBER, PURPLE, TEAL, SKY, RED, GRAY]
TITLE_SIZE = 28
SUBTITLE_SIZE = 20
BODY_SIZE = 16
TICK_SIZE = 15
LABEL_SIZE = 17
NOTE_SIZE = 14
VALUE_SIZE = 16
STAT_SLUGS = [
    "fig_5_1_dataset_inventory",
    "fig_5_2_category_distribution",
    "fig_5_3_baseline_comparison",
    "fig_5_4_failure_distribution",
    "fig_5_5_chain_replay_matrix",
    "fig_5_6_openclaw_rerun",
]


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


def wrap_label(text: str, width: int = 14) -> str:
    text = text.replace(" / ", "/")
    return "<br>".join(textwrap.wrap(text, width=width, break_long_words=False))


def wrapped(items: Iterable[str], width: int = 14) -> list[str]:
    return [wrap_label(item, width) for item in items]


def base_layout(fig: go.Figure, title: str, *, height: int = HEIGHT) -> None:
    fig.update_layout(
        title={
            "text": title,
            "x": 0.035,
            "xanchor": "left",
            "y": 0.965,
            "yanchor": "top",
            "font": {"size": TITLE_SIZE, "family": FONT, "color": INK},
        },
        width=WIDTH,
        height=height,
        paper_bgcolor=PAPER,
        plot_bgcolor=PLOT,
        font={"family": FONT, "size": BODY_SIZE, "color": INK},
        margin={"l": 105, "r": 65, "t": 115, "b": 95},
        legend={
            "orientation": "h",
            "x": 1,
            "y": 1.06,
            "xanchor": "right",
            "yanchor": "bottom",
            "font": {"size": BODY_SIZE, "family": FONT},
        },
        bargap=0.22,
        bargroupgap=0.12,
        hovermode=False,
    )


def axis_style(fig: go.Figure, *, x_title: str | None = None, y_title: str | None = None) -> None:
    fig.update_xaxes(
        title_text=x_title,
        title_font={"size": LABEL_SIZE, "family": FONT, "color": INK},
        tickfont={"size": TICK_SIZE, "family": FONT, "color": INK},
        showgrid=True,
        gridcolor=GRID,
        gridwidth=1,
        zeroline=False,
        linecolor=AXIS,
        linewidth=1.2,
        ticks="outside",
        tickcolor=AXIS,
        mirror=False,
    )
    fig.update_yaxes(
        title_text=y_title,
        title_font={"size": LABEL_SIZE, "family": FONT, "color": INK},
        tickfont={"size": TICK_SIZE, "family": FONT, "color": INK},
        showgrid=False,
        zeroline=False,
        linecolor=AXIS,
        linewidth=1.2,
        ticks="outside",
        tickcolor=AXIS,
        mirror=False,
    )


def save(fig: go.Figure, slug: str, *, height: int = HEIGHT) -> None:
    base_layout(fig, fig.layout.title.text or slug, height=height)
    png = OUT / f"{slug}.png"
    if png.exists():
        png.unlink()
    fig.write_image(png, width=WIDTH, height=height, scale=SCALE)
    print(f"generated {png}")


def add_source_note(fig: go.Figure, text: str, *, y: float = -0.12) -> None:
    fig.add_annotation(
        text=text,
        xref="paper",
        yref="paper",
        x=0,
        y=y,
        showarrow=False,
        align="left",
        font={"size": NOTE_SIZE, "family": FONT, "color": MUTED},
    )


def text_values(values: Sequence[int], suffix: str = "") -> list[str]:
    return [f"{value}{suffix}" for value in values]


def fig_5_1_dataset_inventory() -> None:
    _, expected, files = load_scenario_stats()
    yaml_total = sum(yaml_counts().values())

    labels = ["playground<br>JSON", "agent<br>JSON", "YAML<br>场景资产", "公开映射<br>新增", "Agent gate<br>单元测试", "链路回放"]
    values = [files["playground.json"], files["agent.json"], yaml_total, 40, 125, 11]

    fig = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"type": "xy"}, {"type": "domain"}]],
        column_widths=[0.62, 0.38],
        horizontal_spacing=0.12,
        subplot_titles=("数据来源规模", "358 个主实验样本预期决策"),
    )
    fig.add_bar(
        x=labels,
        y=values,
        text=text_values(values),
        textposition="outside",
        textfont={"size": VALUE_SIZE, "family": FONT, "color": INK},
        marker={"color": PALETTE[: len(values)], "line": {"color": AXIS, "width": 1.2}},
        cliponaxis=False,
        showlegend=False,
        row=1,
        col=1,
    )
    fig.add_pie(
        labels=["BLOCK", "MODIFY", "ALLOW"],
        values=[expected["BLOCK"], expected["MODIFY"], expected["ALLOW"]],
        hole=0.55,
        textinfo="percent",
        textposition="inside",
        textfont={"size": 17, "family": FONT, "color": PAPER},
        marker={"colors": [RED, AMBER, GREEN], "line": {"color": PAPER, "width": 5}},
        sort=False,
        showlegend=True,
        row=1,
        col=2,
    )
    fig.update_layout(title_text="实验数据与证据口径")
    axis_style(fig, y_title="场景 / 测试数量")
    fig.update_yaxes(range=[0, max(values) + 45], row=1, col=1)
    fig.update_annotations(font={"size": SUBTITLE_SIZE, "family": FONT, "color": INK})
    fig.add_annotation(
        text="322 BLOCK / 16 MODIFY / 20 ALLOW",
        xref="paper",
        yref="paper",
        x=0.825,
        y=0.18,
        showarrow=False,
        font={"size": 15, "family": FONT, "color": MUTED},
    )
    fig.add_annotation(
        text="147 = 107 原有 + 40 新增",
        xref="x",
        yref="y",
        x=2,
        y=yaml_total + 22,
        showarrow=False,
        font={"size": NOTE_SIZE, "family": FONT, "color": MUTED},
    )
    save(fig, "fig_5_1_dataset_inventory")


def fig_5_2_category_distribution() -> None:
    categories, _, _ = load_scenario_stats()
    top_items = categories.most_common(16)
    labels = [name for name, _ in top_items][::-1]
    values = [value for _, value in top_items][::-1]

    fig = go.Figure()
    fig.add_bar(
        x=values,
        y=wrapped(labels, 22),
        orientation="h",
        text=text_values(values),
        textposition="outside",
        textfont={"size": VALUE_SIZE, "family": FONT, "color": INK},
        marker={"color": BLUE, "line": {"color": AXIS, "width": 1.1}},
        cliponaxis=False,
        showlegend=False,
    )
    fig.update_layout(title_text="主实验代表性类别样本分布")
    axis_style(fig, x_title="场景数量")
    fig.update_xaxes(range=[0, max(values) + 3])
    add_source_note(fig, "按 358 个 JSON 主实验样本统计，展示样本数最高的 16 个类别。")
    save(fig, "fig_5_2_category_distribution")


def fig_5_3_baseline_comparison() -> None:
    labels = ["未保护直连<br>LLM", "fast<br>rules-only", "balanced<br>默认策略"]
    correct = [20, 269, 274]
    total = 358
    missed = [total - value for value in correct]
    rates = [value / total * 100 for value in correct]

    fig = go.Figure()
    fig.add_bar(
        x=labels,
        y=correct,
        name="符合预期",
        text=[f"{value}/358<br>{rate:.1f}%" for value, rate in zip(correct, rates)],
        textposition="inside",
        insidetextanchor="middle",
        textfont={"size": VALUE_SIZE, "family": FONT, "color": PAPER},
        marker={"color": [SLATE, BLUE, GREEN], "line": {"color": AXIS, "width": 1.1}},
    )
    fig.add_bar(
        x=labels,
        y=missed,
        name="未符合预期",
        text=text_values(missed),
        textposition="inside",
        textfont={"size": VALUE_SIZE, "family": FONT, "color": INK},
        marker={"color": LIGHT, "line": {"color": AXIS, "width": 1.0}},
    )
    fig.update_layout(title_text="Baseline 与默认策略安全边界对比", barmode="stack", showlegend=False)
    axis_style(fig, y_title="场景数 / 358")
    fig.update_yaxes(range=[0, 392])
    add_source_note(fig, "MODIFY 被 BLOCK 视为安全边界有效；balanced 漏报 84 个，fast 漏报 89 个。")
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
    fast = [10, 11, 10, 6, 5, 4, 5, 4, 3, 3]
    balanced = [10, 10, 9, 6, 5, 4, 4, 4, 3, 3]

    fig = go.Figure()
    fig.add_bar(
        x=fast[::-1],
        y=wrapped(labels[::-1], 24),
        orientation="h",
        name="fast 漏报",
        text=text_values(fast[::-1]),
        textposition="outside",
        textfont={"size": VALUE_SIZE, "family": FONT, "color": INK},
        marker={"color": SKY, "line": {"color": AXIS, "width": 1.1}},
        cliponaxis=False,
    )
    fig.add_bar(
        x=balanced[::-1],
        y=wrapped(labels[::-1], 24),
        orientation="h",
        name="balanced 漏报",
        text=text_values(balanced[::-1]),
        textposition="outside",
        textfont={"size": VALUE_SIZE, "family": FONT, "color": INK},
        marker={"color": RED, "line": {"color": AXIS, "width": 1.1}},
        cliponaxis=False,
    )
    fig.update_layout(title_text="balanced 漏报类别分布", barmode="group")
    axis_style(fig, x_title="漏报数")
    fig.update_xaxes(range=[0, 13.2], dtick=2)
    add_source_note(fig, "来源：baseline 复算；balanced 漏报总数为 84，其中 playground=50、agent=34。")
    save(fig, "fig_5_4_failure_distribution")


def fig_5_5_chain_replay_matrix() -> None:
    rows = [f"CHAIN-{i:02d}" for i in range(1, 12)]
    cols = ["RBAC", "参数", "上下文", "确认", "执行", "清洗", "Trace"]
    matrix = [
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
    text = [["是" if value else "" for value in row] for row in matrix]

    fig = go.Figure()
    fig.add_heatmap(
        z=matrix,
        x=cols,
        y=rows,
        text=text,
        texttemplate="%{text}",
        textfont={"size": 16, "family": FONT, "color": PAPER},
        colorscale=[[0, "#f8fafc"], [0.49, "#f8fafc"], [0.5, "#1d4ed8"], [1, "#1d4ed8"]],
        showscale=False,
        xgap=3,
        ygap=3,
        hoverinfo="skip",
    )
    fig.update_layout(title_text="Agent 工具链离线回放覆盖矩阵")
    axis_style(fig)
    fig.update_xaxes(side="top")
    fig.update_yaxes(autorange="reversed")
    add_source_note(fig, "11/11 passed；矩阵展示每个链路案例覆盖的门控或证据类型。")
    save(fig, "fig_5_5_chain_replay_matrix")


def fig_5_6_openclaw_rerun() -> None:
    labels = [
        "OC-01<br>HTTP safe",
        "OC-02<br>HTTP block",
        "TG-01<br>Telegram safe",
        "TG-02<br>Telegram block",
        "TG-03<br>Indirect",
    ]
    latency = [10279, 66, 8698, 47, 1546]
    status = ["ALLOW + 工具", "BLOCK", "ALLOW + 工具", "BLOCK", "ALLOW + 回显风险"]
    colors = [GREEN, RED, GREEN, RED, AMBER]

    fig = go.Figure()
    fig.add_bar(
        x=labels,
        y=latency,
        text=[f"{value} ms<br>{label}" for value, label in zip(latency, status)],
        textposition="outside",
        textfont={"size": 15, "family": FONT, "color": INK},
        marker={"color": colors, "line": {"color": AXIS, "width": 1.1}},
        cliponaxis=False,
        showlegend=False,
    )
    fig.update_layout(title_text="OpenClaw / Telegram 真实链路复测耗时")
    axis_style(fig, y_title="总耗时 ms")
    fig.update_yaxes(range=[0, 11800], dtick=2000)
    add_source_note(fig, "安全摘要请求执行 openclaw_summarize；阻断请求无工具执行，TG-03 暴露输出回显控制不足。")
    save(fig, "fig_5_6_openclaw_rerun")


def delete_old_stat_figures() -> None:
    for slug in STAT_SLUGS:
        for ext in ("png", "pdf", "svg", "jpg", "jpeg", "webp"):
            path = OUT / f"{slug}.{ext}"
            if path.exists():
                path.unlink()
                print(f"deleted {path}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    delete_old_stat_figures()
    for fn in [
        fig_5_1_dataset_inventory,
        fig_5_2_category_distribution,
        fig_5_3_baseline_comparison,
        fig_5_4_failure_distribution,
        fig_5_5_chain_replay_matrix,
        fig_5_6_openclaw_rerun,
    ]:
        fn()


if __name__ == "__main__":
    main()
