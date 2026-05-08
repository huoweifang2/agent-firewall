#!/usr/bin/env python3
"""Generate schematic thesis figures through AutoFigure-Edit prompts.

When AUTOFIGURE_EDIT_DIR and OPENAI_API_KEY are available, this script calls
the external AutoFigure-Edit CLI described in its README and converts the
resulting editable SVG into PDF for LaTeX. If the external toolchain is not
configured, the script writes the same prompt files and produces transparent
fallback SVG/PNG/PDF assets with metadata that records the fallback renderer.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle


ROOT = Path(__file__).resolve().parent
PROMPT_DIR = ROOT / "figures" / "autofigure" / "prompts"
OUTPUT_DIR = ROOT / "figures" / "autofigure" / "outputs"
PDF_DIR = ROOT / "figures" / "autofigure" / "pdf"

INK = "#172033"
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
PINK = "#fce7f3"

STYLE_GUIDANCE = """Style requirements:
Use the uploaded or configured reference image style when available. The target visual language is a paper-style process diagram: a large dashed outer frame, pastel horizontal lanes, dashed rounded lane boundaries, thick light-gray arrows, compact icon-like cards, a larger illustrated role/icon block on the left of each lane, and dense but readable labels. Keep it academic and clean; do not use generic plain boxes only.
"""


@dataclass(frozen=True)
class FigureSpec:
    slug: str
    title: str
    prompt: str
    width: float = 7.8
    height: float = 3.9


FIGURES: tuple[FigureSpec, ...] = (
    FigureSpec(
        slug="fig_trust_boundaries",
        title="系统资产流转与主要信任边界",
        prompt="""Draw a clean academic vector diagram in Chinese for an Agent-Firewall thesis.
Show a left-to-right asset flow with five main nodes: 入口适配器/外部消息, 安全壳入口/会话与allowlist, Proxy /v1/scan/确定性输入扫描, Agent Runtime/工具计划与门控, OpenClaw/MCP/工具输出.
Mark three trust boundaries under the flow: 外部消息进入本机运行时, 模型建议进入真实工具执行, 工具结果回流到模型上下文.
Use simple icon-like cards, pastel swimlanes, thick arrows, no invented modules, and leave whitespace for a LaTeX caption.""",
    ),
    FigureSpec(
        slug="fig_architecture",
        title="Agent-Firewall总体架构",
        prompt="""Draw a layered architecture diagram in Chinese for the Agent-Firewall system.
Use only these components: 消息入口适配器, Nuxt/Vuetify 控制台, Agent Runtime :8002, Proxy Service :8000, 本地SQLite与memory cache, OpenClaw/MCP Runtime, 回复通道.
Show that the Agent Runtime calls Proxy /v1/scan and uses pre/post tool gates before OpenClaw/MCP tools. Show that the console connects to Agent Runtime and Proxy Service.
State visually that Telegram is only one ingress adapter, while the firewall wraps OpenClaw tool execution.
Academic style, editable SVG, clear arrows, compact labels.""",
        height=4.2,
    ),
    FigureSpec(
        slug="fig_proxy_pipeline",
        title="Proxy scan-only检测流水线",
        prompt="""Draw a horizontal flowchart in Chinese for the Proxy Service scan-only pipeline.
Nodes in order: parse 消息规范化, intent 攻击意图分类, rules denylist/长度/编码, scanners 本地扫描, decision 风险聚合, audit 请求日志.
From decision branch to ALLOW 继续Agent运行, MODIFY 脱敏/改写, BLOCK 暂停或拒绝.
Make clear that the proxy does not call the LLM and returns deterministic ALLOW/MODIFY/BLOCK decisions.""",
        height=3.6,
    ),
    FigureSpec(
        slug="fig_agent_pipeline",
        title="Agent Runtime运行图与工具安全边界",
        prompt="""Draw a Chinese thesis flow diagram for the Agent Runtime graph-compatible runner.
Main sequence: input 会话/清洗, intent 意图记录, policy 角色工具, router 工具规划, pre-tool gate RBAC/Schema/预算/确认, executor Internal/OpenClaw/MCP, post-tool gate PII/密钥/注入清洗, llm call Proxy预扫与模型响应, response 最终回复, memory/Trace.
Highlight three protected boundaries: before model call, before tool execution, after tool execution.
Use neutral academic styling and do not add unmentioned frameworks.""",
        width=8.2,
        height=4.1,
    ),
    FigureSpec(
        slug="fig_intervention_flow",
        title="Intervention人工审批闭环",
        prompt="""Draw a Chinese flowchart for the human intervention approval loop.
Flow: 暂停触发 from Proxy BLOCK or sensitive tool confirmation, 创建审批项 /v1/interventions status=pending, Approvals/Audit 本地控制台审核, approved path to Bridge worker 轮询approved并重放请求, Agent Runtime 验证审批状态, 完成并更新Trace.
Also show rejected path: 状态更新为 rejected, 原请求不执行真实敏感工具.
Keep arrows and labels clear for a thesis figure.""",
        height=3.7,
    ),
    FigureSpec(
        slug="fig_tool_gate_state_machine",
        title="工具调用门控状态机",
        prompt="""Draw a state-machine style Chinese diagram for tool-call gating in Agent-Firewall.
States: 工具计划生成, pre-tool检查, ALLOW, MODIFY, BLOCK, REQUIRE_CONFIRMATION, 审批通过重放, 工具执行, post-tool检查, PASS, REDACT, BLOCK_OUTPUT, Trace落盘, 最终回复.
Show that BLOCK and REQUIRE_CONFIRMATION stop execution before real tools, while REDACT/BLOCK_OUTPUT happen after tool execution before LLM context.
Use flowchart cards, guarded arrows, pastel swimlanes, and thesis-neutral terminology.""",
        height=4.1,
    ),
    FigureSpec(
        slug="fig_delegation",
        title="子Agent委派链的门控与审计",
        prompt="""Draw a Chinese schematic for sub-agent delegation governance.
Components: Main Agent receives task, Gate checks role/parameters/budget, Subagent/Tool from OpenClaw or MCP executes only if allowed, Trace records delegation evidence.
Call out risks: low-privilege user inducing high-privilege delegation, excessive context sent to sub-agent.
Call out control: delegation is modeled as an auditable protected tool call with quotas and post-tool cleaning.
Use concise thesis labels and no speculative entities.""",
        height=3.8,
    ),
    FigureSpec(
        slug="fig_trace_evidence",
        title="Trace审计证据链",
        prompt="""Draw a Chinese layered evidence-chain diagram for Agent-Firewall Trace.
Show sequential evidence blocks: 输入扫描 risk flags decision, 工具计划 tool name args, Pre gate RBAC Schema Confirm, Tool exec provider latency, Post gate redaction block, 最终回复.
Below them show a unified Trace/Audit store that records time, reason, result, sanitized preview, and cross-boundary decisions.
Make clear that Trace answers why a request was blocked, where it was blocked, whether a real tool executed, and whether raw output entered model context.""",
        height=3.7,
    ),
    FigureSpec(
        slug="fig_evidence_scope",
        title="实验口径与证据链总览",
        prompt="""Draw a Chinese overview diagram for thesis experimental evidence scope.
Left lane: 离线确定性复核, including pytest, mock LLM, static red-team scenarios, pure memory state, 11 agent-chain replay cases.
Right lane: 本机联调, including Telegram DM ingress, OpenClaw Gateway health, runtime contract, intervention approval, SQLite Trace/request/intervention evidence.
Bottom conclusion: two evidence types complement each other; no external benchmark numbers are mixed into deterministic conclusions.
Use a two-lane academic layout with clear boundaries and restrained colors.""",
        height=3.8,
    ),
)


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
            "text.color": INK,
        }
    )


def _write_prompts(prompt_dir: Path) -> None:
    prompt_dir.mkdir(parents=True, exist_ok=True)
    for spec in FIGURES:
        prompt = STYLE_GUIDANCE.strip() + "\n\n" + spec.prompt.strip() + "\n"
        (prompt_dir / f"{spec.slug}.md").write_text(prompt, encoding="utf-8")


def _wrap(text: str, width: int = 13) -> str:
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False))


def _canvas(spec: FigureSpec):
    fig, ax = plt.subplots(figsize=(spec.width, spec.height))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.02, 0.965, spec.title, fontsize=14, fontweight="bold", ha="left", va="top")
    return fig, ax


def _box(ax, x: float, y: float, w: float, h: float, text: str, fc: str = GRAY, fs: float = 9.0, lw: float = 1.1):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        fc=fc,
        ec=LINE,
        lw=lw,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, linespacing=1.22)
    return patch


def _note(ax, x: float, y: float, w: float, h: float, text: str, fc: str = "white", fs: float = 8.1):
    return _box(ax, x, y, w, h, text, fc=fc, fs=fs, lw=0.85)


def _arrow(ax, start, end, color: str = LINE, lw: float = 1.25, rad: float = 0.0):
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


def _title_note(ax, text: str) -> None:
    ax.text(0.02, 0.04, text, fontsize=8.2, color=MUTED, ha="left", va="bottom")


def _style_canvas(spec: FigureSpec):
    fig, ax = plt.subplots(figsize=(spec.width, spec.height))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.965, spec.title, fontsize=15, fontweight="bold", ha="center", va="top")
    frame = FancyBboxPatch(
        (0.018, 0.065),
        0.964,
        0.81,
        boxstyle="round,pad=0.006,rounding_size=0.008",
        fc="white",
        ec="#8a8f98",
        lw=1.2,
        linestyle=(0, (4, 3)),
    )
    ax.add_patch(frame)
    return fig, ax


def _icon_panel(ax, x: float, y: float, w: float, h: float, kind: str, fc: str) -> None:
    panel = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.008,rounding_size=0.012",
        fc="white",
        ec="#6b83c6",
        lw=0.9,
        linestyle=(0, (2, 2)),
    )
    ax.add_patch(panel)
    cx, cy = x + w * 0.43, y + h * 0.60
    head = Circle((cx, cy), min(w, h) * 0.20, fc=fc, ec=LINE, lw=1.0)
    ax.add_patch(head)
    ax.add_patch(Circle((cx - w * 0.055, cy + h * 0.02), min(w, h) * 0.025, fc="#22d3ee", ec=LINE, lw=0.5))
    ax.add_patch(Circle((cx + w * 0.055, cy + h * 0.02), min(w, h) * 0.025, fc="#22d3ee", ec=LINE, lw=0.5))
    ax.add_patch(Rectangle((x + w * 0.24, y + h * 0.13), w * 0.38, h * 0.22, fc="#f8fafc", ec=LINE, lw=0.9))
    ax.add_patch(Rectangle((x + w * 0.18, y + h * 0.08), w * 0.52, h * 0.06, fc="#a16207", ec=LINE, lw=0.7))
    if kind in {"scan", "trace", "evidence"}:
        ax.add_patch(Circle((x + w * 0.72, y + h * 0.67), min(w, h) * 0.08, fc="#dbeafe", ec=LINE, lw=0.8))
        ax.plot([x + w * 0.77, x + w * 0.88], [y + h * 0.58, y + h * 0.47], color=LINE, lw=1.3)
    elif kind in {"gate", "approve"}:
        ax.add_patch(Rectangle((x + w * 0.66, y + h * 0.53), w * 0.22, h * 0.26, fc="#fef9c3", ec=LINE, lw=0.8))
        ax.plot([x + w * 0.70, x + w * 0.74, x + w * 0.83], [y + h * 0.66, y + h * 0.59, y + h * 0.72], color="#16a34a", lw=1.4)
    elif kind in {"tool", "agent"}:
        ax.add_patch(Rectangle((x + w * 0.66, y + h * 0.53), w * 0.24, h * 0.20, fc="#fde68a", ec=LINE, lw=0.8))
        ax.add_patch(Rectangle((x + w * 0.70, y + h * 0.63), w * 0.16, h * 0.06, fc="#facc15", ec=LINE, lw=0.6))
    else:
        ax.add_patch(Rectangle((x + w * 0.66, y + h * 0.52), w * 0.20, h * 0.25, fc="#e2e8f0", ec=LINE, lw=0.8))
        ax.plot([x + w * 0.70, x + w * 0.82], [y + h * 0.68, y + h * 0.68], color=LINE, lw=0.8)
        ax.plot([x + w * 0.70, x + w * 0.82], [y + h * 0.60, y + h * 0.60], color=LINE, lw=0.8)


def _node_icon(ax, x: float, y: float, w: float, h: float, kind: str) -> None:
    ix, iy = x + w * 0.36, y + h * 0.53
    if kind in {"folder", "tool", "provider"}:
        ax.add_patch(Rectangle((ix, iy), w * 0.28, h * 0.22, fc="#facc15", ec=LINE, lw=0.7))
        ax.add_patch(Rectangle((ix + w * 0.03, iy + h * 0.17), w * 0.10, h * 0.06, fc="#fde68a", ec=LINE, lw=0.5))
    elif kind in {"gate", "approve", "decision"}:
        ax.add_patch(Rectangle((ix, iy), w * 0.28, h * 0.24, fc="#fef9c3", ec=LINE, lw=0.7))
        ax.plot([ix + w * 0.06, ix + w * 0.12, ix + w * 0.23], [iy + h * 0.13, iy + h * 0.07, iy + h * 0.19], color="#16a34a", lw=1.2)
    elif kind in {"trace", "chart"}:
        ax.add_patch(Rectangle((ix, iy), w * 0.30, h * 0.24, fc="#e0f2fe", ec=LINE, lw=0.7))
        ax.plot([ix + w * 0.05, ix + w * 0.10, ix + w * 0.18, ix + w * 0.26], [iy + h * 0.06, iy + h * 0.16, iy + h * 0.10, iy + h * 0.20], color="#2563eb", lw=1.1)
    elif kind in {"block", "risk"}:
        ax.add_patch(Circle((ix + w * 0.15, iy + h * 0.12), w * 0.12, fc="#fecaca", ec=LINE, lw=0.7))
        ax.plot([ix + w * 0.08, ix + w * 0.22], [iy + h * 0.05, iy + h * 0.19], color="#dc2626", lw=1.1)
    else:
        ax.add_patch(Rectangle((ix, iy), w * 0.25, h * 0.28, fc="#f8fafc", ec=LINE, lw=0.7))
        ax.plot([ix + w * 0.05, ix + w * 0.20], [iy + h * 0.19, iy + h * 0.19], color=LINE, lw=0.7)
        ax.plot([ix + w * 0.05, ix + w * 0.20], [iy + h * 0.12, iy + h * 0.12], color=LINE, lw=0.7)


def _styled_node(ax, x: float, y: float, w: float, h: float, label: str, icon: str = "doc") -> None:
    card = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.006,rounding_size=0.008",
        fc="white",
        ec="#6b83c6",
        lw=0.8,
        linestyle=(0, (2, 2)),
    )
    ax.add_patch(card)
    _node_icon(ax, x, y, w, h, icon)
    ax.text(x + w / 2, y + h * 0.29, label, ha="center", va="center", fontsize=6.8, linespacing=1.12)


def _thick_arrow(ax, start, end, rad: float = 0.0) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=18,
            lw=3.0,
            color="#a8a8a8",
            alpha=0.92,
            connectionstyle=f"arc3,rad={rad}",
        )
    )


def _styled_lane(ax, y: float, h: float, title: str, color: str, icon_kind: str, nodes: list[tuple[str, str]]) -> None:
    lane = FancyBboxPatch(
        (0.045, y),
        0.91,
        h,
        boxstyle="round,pad=0.004,rounding_size=0.010",
        fc=color,
        ec="#7e8aa2",
        lw=0.95,
        linestyle=(0, (3, 2)),
        alpha=0.78,
    )
    ax.add_patch(lane)
    ax.text(0.50, y + h - 0.027, title, ha="center", va="top", fontsize=10.2, fontweight="bold", color=INK)
    _icon_panel(ax, 0.065, y + h * 0.16, 0.105, h * 0.62, icon_kind, color)

    n = len(nodes)
    x0, x1 = 0.235, 0.925
    gap = 0.016 if n > 1 else 0
    w = min(0.115, (x1 - x0 - gap * (n - 1)) / n)
    total = n * w + (n - 1) * gap
    start = x0 + (x1 - x0 - total) / 2
    node_h = min(0.118, h * 0.47)
    node_y = y + h * 0.32
    centers: list[tuple[float, float]] = []
    for idx, (label, icon) in enumerate(nodes):
        x = start + idx * (w + gap)
        _styled_node(ax, x, node_y, w, node_h, label, icon)
        centers.append((x + w / 2, node_y + node_h / 2))
        if idx:
            prev_x = start + (idx - 1) * (w + gap)
            _thick_arrow(ax, (prev_x + w + 0.004, node_y + node_h / 2), (x - 0.004, node_y + node_h / 2))
    if centers:
        _thick_arrow(ax, (0.170, y + h * 0.47), (start - 0.006, node_y + node_h / 2))


def _style_lane_positions(count: int) -> tuple[float, float]:
    usable_top = 0.805
    usable_bottom = 0.145
    gap = 0.018
    h = (usable_top - usable_bottom - gap * (count - 1)) / count
    return tuple(usable_top - h - i * (h + gap) for i in range(count)), h


def _render_style_lanes(
    spec: FigureSpec,
    output_dir: Path,
    lanes: list[dict[str, object]],
    footer: str,
) -> None:
    fig, ax = _style_canvas(spec)
    ys, h = _style_lane_positions(len(lanes))
    for y, lane in zip(ys, lanes):
        _styled_lane(
            ax,
            y,
            h,
            str(lane["title"]),
            str(lane["color"]),
            str(lane.get("icon", "doc")),
            list(lane["nodes"]),  # type: ignore[arg-type]
        )
    ax.text(0.5, 0.092, footer, ha="center", va="center", fontsize=8.2, color=MUTED)
    _save_fallback(fig, output_dir)


def _render_trust_boundaries_style(spec: FigureSpec, output_dir: Path) -> None:
    _render_style_lanes(
        spec,
        output_dir,
        [
            {"title": "Step 1: 外部消息进入本机运行时", "color": BLUE, "icon": "agent", "nodes": [("外部\n消息", "doc"), ("入口\n适配器", "folder"), ("会话\nallowlist", "gate")]},
            {"title": "Step 2: 模型建议进入真实工具执行", "color": GREEN, "icon": "gate", "nodes": [("LLM\n工具计划", "doc"), ("pre-tool\ngate", "gate"), ("真实\n工具", "tool")]},
            {"title": "Step 3: 工具结果回流到模型上下文", "color": PURPLE, "icon": "trace", "nodes": [("工具\n输出", "doc"), ("post-tool\n清洗", "gate"), ("模型\n上下文", "trace")]},
        ],
        "每个跨边界动作均由后端策略和Trace记录，而不是由自然语言承诺决定。",
    )


def _render_architecture_style(spec: FigureSpec, output_dir: Path) -> None:
    _render_style_lanes(
        spec,
        output_dir,
        [
            {"title": "Step 1: 入口与控制面", "color": BLUE, "icon": "agent", "nodes": [("消息入口\n适配器", "doc"), ("Nuxt/Vuetify\n控制台", "chart"), ("回复\n通道", "doc")]},
            {"title": "Step 2: Agent-Firewall 安全层", "color": GREEN, "icon": "gate", "nodes": [("Agent Runtime\n:8002", "tool"), ("Proxy Service\n:8000", "gate"), ("interventions\n审批队列", "approve")]},
            {"title": "Step 3: 本机运行时与证据", "color": YELLOW, "icon": "tool", "nodes": [("SQLite\nmemory", "folder"), ("OpenClaw/MCP\nRuntime", "provider"), ("Trace/Audit\n证据", "trace")]},
        ],
        "Agent-Firewall 包裹 OpenClaw 工具执行；Telegram 只是入口适配器之一。",
    )


def _render_proxy_pipeline_style(spec: FigureSpec, output_dir: Path) -> None:
    _render_style_lanes(
        spec,
        output_dir,
        [
            {"title": "Step 1: Scan-only 输入检测流水线", "color": BLUE, "icon": "scan", "nodes": [("parse\n规范化", "doc"), ("intent\n意图", "trace"), ("rules\n规则", "gate"), ("scanners\n扫描", "scan"), ("decision\n聚合", "decision"), ("audit\n日志", "trace")]},
            {"title": "Step 2: 确定性决策输出", "color": GREEN, "icon": "gate", "nodes": [("ALLOW\n继续", "gate"), ("MODIFY\n清洗", "approve"), ("BLOCK\n暂停", "block"), ("intervention\n审批", "approve")]},
        ],
        "Proxy 不直接调用 LLM，仅返回 ALLOW / MODIFY / BLOCK 决策。",
    )


def _render_agent_pipeline_style(spec: FigureSpec, output_dir: Path) -> None:
    _render_style_lanes(
        spec,
        output_dir,
        [
            {"title": "Step 1: 会话与工具计划", "color": BLUE, "icon": "agent", "nodes": [("input\n会话", "doc"), ("intent\n记录", "trace"), ("policy\n角色", "gate"), ("router\n规划", "tool")]},
            {"title": "Step 2: 工具执行安全边界", "color": GREEN, "icon": "gate", "nodes": [("pre-tool\n门控", "gate"), ("executor\n工具执行", "tool"), ("post-tool\n清洗", "gate")]},
            {"title": "Step 3: 模型响应与审计", "color": PURPLE, "icon": "trace", "nodes": [("llm call\nProxy预扫", "scan"), ("response\n最终回复", "doc"), ("memory\nTrace", "trace")]},
        ],
        "模型调用前、真实工具执行前、工具输出入上下文前三处边界均显式门控。",
    )


def _render_intervention_flow_style(spec: FigureSpec, output_dir: Path) -> None:
    _render_style_lanes(
        spec,
        output_dir,
        [
            {"title": "Step 1: Approved path", "color": GREEN, "icon": "approve", "nodes": [("暂停\n触发", "block"), ("pending\n审批项", "doc"), ("控制台\n审核", "approve"), ("Bridge\n重放", "tool"), ("完成\nTrace", "trace")]},
            {"title": "Step 2: Rejected path", "color": RED, "icon": "gate", "nodes": [("本地\n拒绝", "block"), ("状态\nrejected", "doc"), ("不执行\n真实工具", "block"), ("Trace\n记录", "trace")]},
        ],
        "审批通过才携带 approved_intervention_id 重放；拒绝路径不会执行敏感工具。",
    )


def _render_tool_gate_state_machine_style(spec: FigureSpec, output_dir: Path) -> None:
    _render_style_lanes(
        spec,
        output_dir,
        [
            {"title": "Step 1: Pre-tool decision", "color": BLUE, "icon": "gate", "nodes": [("工具计划\n生成", "doc"), ("pre-tool\n检查", "gate"), ("ALLOW /\nMODIFY", "approve"), ("BLOCK /\nCONFIRM", "block")]},
            {"title": "Step 2: Execution after approval", "color": YELLOW, "icon": "tool", "nodes": [("审批通过\n重放", "approve"), ("真实工具\n执行", "tool"), ("工具结果\n返回", "doc")]},
            {"title": "Step 3: Post-tool decision", "color": PURPLE, "icon": "trace", "nodes": [("post-tool\n检查", "gate"), ("PASS /\nREDACT", "approve"), ("BLOCK\nOUTPUT", "block"), ("Trace\n落盘", "trace"), ("最终\n回复", "doc")]},
        ],
        "BLOCK 与 CONFIRM 在真实工具前生效；REDACT 与 BLOCK_OUTPUT 在进入模型上下文前生效。",
    )


def _render_delegation_style(spec: FigureSpec, output_dir: Path) -> None:
    _render_style_lanes(
        spec,
        output_dir,
        [
            {"title": "Step 1: 委派作为受保护工具计划", "color": BLUE, "icon": "agent", "nodes": [("Main Agent\n任务", "doc"), ("Gate\n角色/预算", "gate"), ("Subagent/Tool\n执行", "tool"), ("Trace\n证据链", "trace")]},
            {"title": "Step 2: 委派风险", "color": RED, "icon": "scan", "nodes": [("低权限\n代办", "risk"), ("过量\n上下文", "risk"), ("跨工具\n扩散", "risk")]},
            {"title": "Step 3: 治理控制", "color": GREEN, "icon": "approve", "nodes": [("RBAC\n校验", "gate"), ("限额\n控制", "approve"), ("post-tool\n清洗", "gate"), ("审计\n追踪", "trace")]},
        ],
        "子Agent委派不绕过防火墙，而是进入同一套工具调用门控与Trace体系。",
    )


def _render_trace_evidence_style(spec: FigureSpec, output_dir: Path) -> None:
    _render_style_lanes(
        spec,
        output_dir,
        [
            {"title": "Step 1: 跨边界事件链", "color": BLUE, "icon": "trace", "nodes": [("输入扫描\nrisk/decision", "scan"), ("工具计划\ntool/args", "doc"), ("Pre gate\nRBAC/Schema", "gate"), ("Tool exec\nprovider/latency", "tool"), ("Post gate\nredaction/block", "gate"), ("最终回复\nsanitized", "doc")]},
            {"title": "Step 2: Trace/Audit 统一证据库", "color": TEAL, "icon": "evidence", "nodes": [("时间", "trace"), ("原因", "doc"), ("结果", "approve"), ("脱敏预览", "scan"), ("阻断层级", "block")]},
        ],
        "Trace 回答为什么拦截、在哪一层拦截、是否执行真实工具、原始结果是否进入上下文。",
    )


def _render_evidence_scope_style(spec: FigureSpec, output_dir: Path) -> None:
    _render_style_lanes(
        spec,
        output_dir,
        [
            {"title": "Step 1: 离线确定性复核", "color": BLUE, "icon": "scan", "nodes": [("pytest", "trace"), ("mock LLM", "doc"), ("静态红队\n场景", "risk"), ("纯内存\n状态", "folder"), ("11类工具链\n回放", "tool")]},
            {"title": "Step 2: 本机联调", "color": GREEN, "icon": "agent", "nodes": [("Telegram\nDM入口", "doc"), ("OpenClaw\nGateway", "provider"), ("runtime\ncontract", "gate"), ("intervention\n审批", "approve"), ("SQLite\nTrace证据", "trace")]},
            {"title": "Step 3: 证据口径", "color": YELLOW, "icon": "evidence", "nodes": [("互为\n补充", "approve"), ("不混用\nbenchmark", "block"), ("只保留\n脱敏证据", "trace")]},
        ],
        "离线证据用于确定性结论，本机联调用于验证真实入口与provider链路连续性。",
    )


def _render_trust_boundaries(spec: FigureSpec, output_dir: Path) -> None:
    fig, ax = _canvas(spec)
    nodes = [
        ("入口适配器\n外部消息", RED),
        ("安全壳入口\n会话 / allowlist", BLUE),
        ("Proxy /v1/scan\n确定性输入扫描", GREEN),
        ("Agent Runtime\n工具计划与门控", YELLOW),
        ("OpenClaw / MCP\n工具输出", GRAY),
    ]
    xs = [0.04, 0.245, 0.45, 0.655, 0.84]
    for i, ((label, color), x) in enumerate(zip(nodes, xs)):
        _box(ax, x, 0.58, 0.14, 0.16, label, color, fs=8.7)
        if i:
            _arrow(ax, (xs[i - 1] + 0.14, 0.66), (x, 0.66))
    notes = [
        ("边界1\n外部消息进入本机运行时", 0.15),
        ("边界2\n模型建议进入真实工具执行", 0.46),
        ("边界3\n工具结果回流到模型上下文", 0.72),
    ]
    for text, x in notes:
        _note(ax, x, 0.26, 0.19, 0.12, text, fs=8)
    _arrow(ax, (0.20, 0.56), (0.245, 0.39), color=RED)
    _arrow(ax, (0.63, 0.56), (0.555, 0.39), color=RED)
    _arrow(ax, (0.90, 0.56), (0.815, 0.39), color=RED)
    _title_note(ax, "外部消息、工具计划和工具输出分别跨越不同信任边界。")
    _save_fallback(fig, output_dir)


def _render_architecture(spec: FigureSpec, output_dir: Path) -> None:
    fig, ax = _canvas(spec)
    _box(ax, 0.05, 0.74, 0.20, 0.12, "消息入口适配器\nTelegram / CLI / Webhook", RED, 8.3)
    _box(ax, 0.40, 0.74, 0.22, 0.12, "Nuxt / Vuetify 控制台\nApprovals / Trace / Settings", BLUE, 8.3)
    _box(ax, 0.76, 0.74, 0.18, 0.12, "回复通道\n原入口返回", GRAY, 8.3)
    _box(ax, 0.13, 0.46, 0.28, 0.14, "Agent Runtime :8002\ngraph-compatible runner\npre/post tool gates", YELLOW, 8.5)
    _box(ax, 0.58, 0.46, 0.28, 0.14, "Proxy Service :8000\n/v1/scan / audit\ninterventions / runtime spec", GREEN, 8.5)
    _box(ax, 0.13, 0.22, 0.28, 0.12, "本地状态\nSQLite + memory cache", GRAY, 8.5)
    _box(ax, 0.58, 0.22, 0.28, 0.12, "OpenClaw / MCP Runtime\nskills / hooks / providers", PURPLE, 8.5)
    _arrow(ax, (0.15, 0.74), (0.22, 0.60))
    _arrow(ax, (0.25, 0.53), (0.58, 0.53))
    _arrow(ax, (0.58, 0.50), (0.41, 0.50))
    _arrow(ax, (0.72, 0.46), (0.72, 0.34))
    _arrow(ax, (0.27, 0.46), (0.27, 0.34))
    _arrow(ax, (0.41, 0.47), (0.58, 0.32), rad=-0.08)
    _arrow(ax, (0.49, 0.74), (0.30, 0.60))
    _arrow(ax, (0.54, 0.74), (0.70, 0.60))
    _arrow(ax, (0.41, 0.58), (0.76, 0.74), rad=0.16)
    _note(ax, 0.18, 0.06, 0.64, 0.08, "核心边界：Agent-Firewall 包裹 OpenClaw 工具执行；Telegram 只是入口适配器之一。", TEAL, fs=8.8)
    _save_fallback(fig, output_dir)


def _render_proxy_pipeline(spec: FigureSpec, output_dir: Path) -> None:
    fig, ax = _canvas(spec)
    nodes = [
        ("parse\n消息规范化", BLUE),
        ("intent\n攻击意图分类", BLUE),
        ("rules\ndenylist / 长度 / 编码", GREEN),
        ("scanners\n本地扫描", YELLOW),
        ("decision\n风险聚合", RED),
        ("audit\n请求日志", GRAY),
    ]
    xs = [0.04, 0.20, 0.36, 0.52, 0.68, 0.84]
    for i, ((label, color), x) in enumerate(zip(nodes, xs)):
        _box(ax, x, 0.58, 0.12, 0.14, label, color, fs=8.2)
        if i:
            _arrow(ax, (xs[i - 1] + 0.12, 0.65), (x, 0.65))
    _note(ax, 0.36, 0.25, 0.13, 0.10, "ALLOW\n继续运行", GREEN)
    _note(ax, 0.53, 0.25, 0.13, 0.10, "MODIFY\n脱敏/改写", PURPLE)
    _note(ax, 0.70, 0.25, 0.13, 0.10, "BLOCK\n暂停或拒绝", RED)
    _arrow(ax, (0.74, 0.58), (0.43, 0.35), color=GREEN)
    _arrow(ax, (0.74, 0.58), (0.595, 0.35), color=PURPLE)
    _arrow(ax, (0.74, 0.58), (0.765, 0.35), color=RED)
    _title_note(ax, "Proxy 为 scan-only 接口，不直接调用 LLM。")
    _save_fallback(fig, output_dir)


def _render_agent_pipeline(spec: FigureSpec, output_dir: Path) -> None:
    fig, ax = _canvas(spec)
    top = [
        ("input\n会话/清洗", GRAY),
        ("intent\n意图记录", GRAY),
        ("policy\n角色工具", BLUE),
        ("router\n工具规划", BLUE),
        ("pre-tool\nRBAC/Schema/预算/确认", GREEN),
        ("executor\nInternal/OpenClaw/MCP", YELLOW),
    ]
    xs = [0.03, 0.18, 0.33, 0.48, 0.63, 0.80]
    for i, ((label, color), x) in enumerate(zip(top, xs)):
        w = 0.13 if i < 4 else 0.15
        _box(ax, x, 0.66, w, 0.13, label, color, fs=7.7)
        if i:
            _arrow(ax, (xs[i - 1] + (0.13 if i - 1 < 4 else 0.15), 0.725), (x, 0.725))
    _box(ax, 0.80, 0.41, 0.15, 0.13, "post-tool\nPII/密钥/注入清洗", ORANGE, fs=7.7)
    _box(ax, 0.63, 0.41, 0.15, 0.13, "llm call\nProxy预扫/模型响应", RED, fs=7.7)
    _box(ax, 0.45, 0.41, 0.14, 0.13, "response\n最终回复", GRAY, fs=7.7)
    _box(ax, 0.26, 0.41, 0.14, 0.13, "memory / Trace\n会话证据", TEAL, fs=7.7)
    _arrow(ax, (0.875, 0.66), (0.875, 0.54))
    _arrow(ax, (0.80, 0.475), (0.78, 0.475))
    _arrow(ax, (0.63, 0.475), (0.59, 0.475))
    _arrow(ax, (0.45, 0.475), (0.40, 0.475))
    _note(ax, 0.18, 0.16, 0.21, 0.11, "边界一\n模型调用前输入预扫", BLUE)
    _note(ax, 0.42, 0.16, 0.21, 0.11, "边界二\n真实工具执行前门控", GREEN)
    _note(ax, 0.66, 0.16, 0.21, 0.11, "边界三\n工具输出进入上下文前清洗", ORANGE)
    _arrow(ax, (0.705, 0.66), (0.54, 0.28), color=RED, rad=-0.08)
    _save_fallback(fig, output_dir)


def _render_intervention_flow(spec: FigureSpec, output_dir: Path) -> None:
    fig, ax = _canvas(spec)
    nodes = [
        ("暂停触发\nProxy BLOCK\n或敏感工具确认", RED),
        ("创建审批项\n/v1/interventions\nstatus=pending", YELLOW),
        ("Approvals/Audit\n本地控制台审核", BLUE),
        ("Bridge worker\n轮询 approved\n重放请求", GREEN),
        ("完成\n回复返回\nTrace更新", GRAY),
    ]
    xs = [0.04, 0.24, 0.45, 0.66, 0.84]
    for i, ((label, color), x) in enumerate(zip(nodes, xs)):
        _box(ax, x, 0.58, 0.15, 0.16, label, color, fs=8)
        if i:
            _arrow(ax, (xs[i - 1] + 0.15, 0.66), (x, 0.66))
    _note(ax, 0.30, 0.25, 0.34, 0.12, "拒绝路径：状态更新为 rejected，原请求不执行真实敏感工具。", "white", fs=8.4)
    _arrow(ax, (0.525, 0.58), (0.47, 0.37), color=RED)
    _arrow(ax, (0.735, 0.58), (0.735, 0.48), color=GREEN)
    _save_fallback(fig, output_dir)


def _render_tool_gate_state_machine(spec: FigureSpec, output_dir: Path) -> None:
    fig, ax = _canvas(spec)
    _box(ax, 0.04, 0.68, 0.14, 0.11, "工具计划生成", BLUE)
    _box(ax, 0.23, 0.68, 0.14, 0.11, "pre-tool检查", GREEN)
    _box(ax, 0.43, 0.78, 0.12, 0.09, "ALLOW", TEAL)
    _box(ax, 0.43, 0.63, 0.12, 0.09, "MODIFY", PURPLE)
    _box(ax, 0.43, 0.47, 0.12, 0.09, "BLOCK", RED)
    _box(ax, 0.43, 0.30, 0.16, 0.10, "REQUIRE\nCONFIRMATION", YELLOW, fs=8)
    _box(ax, 0.63, 0.69, 0.13, 0.11, "工具执行", ORANGE)
    _box(ax, 0.80, 0.69, 0.14, 0.11, "post-tool检查", GREEN)
    _box(ax, 0.80, 0.49, 0.14, 0.09, "PASS / REDACT", TEAL, fs=8)
    _box(ax, 0.62, 0.49, 0.14, 0.09, "BLOCK_OUTPUT", RED, fs=8)
    _box(ax, 0.32, 0.12, 0.16, 0.10, "审批通过重放", YELLOW, fs=8)
    _box(ax, 0.62, 0.12, 0.14, 0.10, "Trace落盘", GRAY)
    _box(ax, 0.80, 0.12, 0.14, 0.10, "最终回复", GRAY)
    _arrow(ax, (0.18, 0.735), (0.23, 0.735))
    _arrow(ax, (0.37, 0.735), (0.43, 0.825))
    _arrow(ax, (0.37, 0.715), (0.43, 0.675))
    _arrow(ax, (0.37, 0.69), (0.43, 0.52), color=RED)
    _arrow(ax, (0.37, 0.68), (0.43, 0.35), color="#d97706")
    _arrow(ax, (0.55, 0.825), (0.63, 0.745))
    _arrow(ax, (0.55, 0.675), (0.63, 0.725))
    _arrow(ax, (0.70, 0.69), (0.70, 0.22), color=MUTED)
    _arrow(ax, (0.76, 0.745), (0.80, 0.745))
    _arrow(ax, (0.87, 0.69), (0.87, 0.58))
    _arrow(ax, (0.80, 0.535), (0.76, 0.535), color=RED)
    _arrow(ax, (0.87, 0.49), (0.87, 0.22))
    _arrow(ax, (0.48, 0.30), (0.40, 0.22), color="#d97706")
    _arrow(ax, (0.48, 0.17), (0.63, 0.17), color="#d97706")
    _arrow(ax, (0.76, 0.17), (0.80, 0.17))
    _title_note(ax, "BLOCK 与 REQUIRE_CONFIRMATION 发生在真实工具执行前；REDACT 与 BLOCK_OUTPUT 发生在工具执行后、进入模型上下文前。")
    _save_fallback(fig, output_dir)


def _render_delegation(spec: FigureSpec, output_dir: Path) -> None:
    fig, ax = _canvas(spec)
    _box(ax, 0.05, 0.60, 0.16, 0.14, "Main Agent\n接收入口任务", BLUE)
    _box(ax, 0.30, 0.60, 0.16, 0.14, "Gate\n角色/参数/预算", GREEN)
    _box(ax, 0.55, 0.60, 0.18, 0.14, "Subagent / Tool\nOpenClaw 或 MCP 能力", YELLOW)
    _box(ax, 0.82, 0.60, 0.13, 0.14, "Trace\n委派证据链", GRAY)
    _arrow(ax, (0.21, 0.67), (0.30, 0.67))
    _arrow(ax, (0.46, 0.67), (0.55, 0.67))
    _arrow(ax, (0.73, 0.67), (0.82, 0.67))
    _note(ax, 0.10, 0.25, 0.20, 0.13, "风险：低权限用户诱导高权限代理代办", RED)
    _note(ax, 0.40, 0.25, 0.20, 0.13, "风险：子Agent接收过量上下文或敏感数据", ORANGE)
    _note(ax, 0.70, 0.25, 0.20, 0.13, "控制：委派作为工具调用审计和限额", TEAL)
    _arrow(ax, (0.13, 0.60), (0.20, 0.38), color=RED)
    _arrow(ax, (0.64, 0.60), (0.50, 0.38), color=RED)
    _arrow(ax, (0.88, 0.60), (0.80, 0.38), color=GREEN)
    _save_fallback(fig, output_dir)


def _render_trace_evidence(spec: FigureSpec, output_dir: Path) -> None:
    fig, ax = _canvas(spec)
    nodes = [
        ("输入扫描\nrisk flags\ndecision", BLUE),
        ("工具计划\ntool name\nargs", GREEN),
        ("Pre gate\nRBAC / Schema\nConfirm", YELLOW),
        ("Tool exec\nprovider\nlatency", ORANGE),
        ("Post gate\nredaction\nblock", RED),
        ("最终回复\nsanitized\nanswer", GRAY),
    ]
    xs = [0.04, 0.20, 0.36, 0.52, 0.68, 0.84]
    for i, ((label, color), x) in enumerate(zip(nodes, xs)):
        _box(ax, x, 0.60, 0.12, 0.15, label, color, fs=7.8)
        if i:
            _arrow(ax, (xs[i - 1] + 0.12, 0.675), (x, 0.675))
        _arrow(ax, (x + 0.06, 0.60), (0.50, 0.39), color=MUTED, rad=0.08 * (i - 2))
    _note(ax, 0.16, 0.22, 0.68, 0.14, "Trace/Audit统一展示：时间、原因、结果、脱敏预览，以及每个跨边界决策。", TEAL, fs=9)
    _title_note(ax, "Trace回答：为什么拦截、在哪一层拦截、是否执行真实工具、原始结果是否进入模型上下文。")
    _save_fallback(fig, output_dir)


def _render_evidence_scope(spec: FigureSpec, output_dir: Path) -> None:
    fig, ax = _canvas(spec)
    _box(ax, 0.07, 0.67, 0.36, 0.12, "离线确定性复核", BLUE, fs=10)
    _box(ax, 0.57, 0.67, 0.36, 0.12, "本机联调", GREEN, fs=10)
    offline = ["pytest", "mock LLM", "静态红队场景", "纯内存状态", "11类Agent工具链回放"]
    local = ["Telegram DM入口", "OpenClaw Gateway健康", "runtime contract", "intervention审批", "SQLite Trace/request/intervention"]
    for i, text in enumerate(offline):
        _note(ax, 0.10, 0.53 - i * 0.075, 0.30, 0.055, text, "white", fs=8.1)
    for i, text in enumerate(local):
        _note(ax, 0.60, 0.53 - i * 0.075, 0.30, 0.055, text, "white", fs=8.1)
    _box(ax, 0.28, 0.12, 0.44, 0.10, "两类证据互补；不混用外部benchmark数值作为确定性结论。", TEAL, fs=8.8)
    _arrow(ax, (0.25, 0.67), (0.42, 0.22), color=BLUE, rad=-0.10)
    _arrow(ax, (0.75, 0.67), (0.58, 0.22), color=GREEN, rad=0.10)
    _save_fallback(fig, output_dir)


RENDERERS = {
    "fig_trust_boundaries": _render_trust_boundaries_style,
    "fig_architecture": _render_architecture_style,
    "fig_proxy_pipeline": _render_proxy_pipeline_style,
    "fig_agent_pipeline": _render_agent_pipeline_style,
    "fig_intervention_flow": _render_intervention_flow_style,
    "fig_tool_gate_state_machine": _render_tool_gate_state_machine_style,
    "fig_delegation": _render_delegation_style,
    "fig_trace_evidence": _render_trace_evidence_style,
    "fig_evidence_scope": _render_evidence_scope_style,
}


def _save_fallback(fig: plt.Figure, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = PDF_DIR / f"{output_dir.name}.pdf"
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / "final.svg", bbox_inches="tight", facecolor="white")
    fig.savefig(output_dir / "template.svg", bbox_inches="tight", facecolor="white")
    fig.savefig(output_dir / "figure.png", bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    metadata = {
        "figure": output_dir.name,
        "renderer": "fallback_matplotlib",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reason": "AUTOFIGURE_EDIT_DIR or OPENAI_API_KEY was not configured.",
        "style": "paper-process-flowchart: dashed frame, pastel lanes, thick gray arrows, icon panels",
        "pdf": str(pdf_path.relative_to(ROOT)),
    }
    (output_dir / "evaluation.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "generation_log.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def _autofigure_entry(autofigure_dir: Path) -> Path:
    for candidate in ("autofigure2.py", "main.py"):
        entry = autofigure_dir / candidate
        if entry.exists():
            return entry
    raise FileNotFoundError(f"No autofigure2.py or main.py found in {autofigure_dir}")


def _convert_svg_to_pdf(svg_path: Path, pdf_path: Path) -> None:
    try:
        import cairosvg
    except Exception as exc:  # pragma: no cover - depends on local optional dependency
        raise RuntimeError(
            "CairoSVG is required to convert AutoFigure SVG outputs to PDF. "
            "Install it with `python -m pip install CairoSVG`."
        ) from exc
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2pdf(url=str(svg_path), write_to=str(pdf_path))


def _run_autofigure(spec: FigureSpec, args: argparse.Namespace, output_dir: Path) -> None:
    autofigure_dir = Path(args.autofigure_dir).expanduser().resolve()
    entry = _autofigure_entry(autofigure_dir)
    prompt_path = PROMPT_DIR / f"{spec.slug}.md"
    cmd = [
        sys.executable,
        str(entry),
        "--method_file",
        str(prompt_path),
        "--output_dir",
        str(output_dir),
        "--provider",
        args.provider,
        "--api_key",
        args.api_key,
        "--svg_model",
        args.svg_model,
        "--image_model",
        args.image_model,
        "--optimize_iterations",
        str(args.optimize_iterations),
    ]
    if args.sam_backend:
        cmd.extend(["--sam_backend", args.sam_backend])
    if args.reference_image_path:
        cmd.extend(["--reference_image_path", str(Path(args.reference_image_path).expanduser())])
    subprocess.run(cmd, cwd=str(autofigure_dir), check=True)
    svg_path = output_dir / "final.svg"
    if not svg_path.exists():
        raise FileNotFoundError(f"AutoFigure did not produce {svg_path}")
    _convert_svg_to_pdf(svg_path, PDF_DIR / f"{spec.slug}.pdf")
    log_path = output_dir / "generation_log.json"
    if log_path.exists():
        log = json.loads(log_path.read_text(encoding="utf-8"))
    else:
        log = {}
    log.update(
        {
            "figure": spec.slug,
            "renderer": "autofigure_edit",
            "entry": entry.name,
            "reference_image_path": args.reference_image_path or None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pdf": str((PDF_DIR / f"{spec.slug}.pdf").relative_to(ROOT)),
        }
    )
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")


def _has_autofigure(args: argparse.Namespace) -> bool:
    return bool(args.autofigure_dir and args.api_key)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AutoFigure-Edit schematic figures for article.tex.")
    parser.add_argument("--autofigure-dir", default=os.environ.get("AUTOFIGURE_EDIT_DIR", ""))
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", ""))
    parser.add_argument("--provider", default=os.environ.get("AUTOFIGURE_PROVIDER", "openai_response"))
    parser.add_argument("--svg-model", default=os.environ.get("AUTOFIGURE_SVG_MODEL", "gpt-5.5"))
    parser.add_argument("--image-model", default=os.environ.get("AUTOFIGURE_IMAGE_MODEL", "gpt-image-2"))
    parser.add_argument("--optimize-iterations", type=int, default=int(os.environ.get("AUTOFIGURE_OPTIMIZE_ITERATIONS", "0")))
    parser.add_argument("--sam-backend", default=os.environ.get("AUTOFIGURE_SAM_BACKEND", ""))
    parser.add_argument("--reference-image-path", default=os.environ.get("AUTOFIGURE_REFERENCE_IMAGE_PATH", ""))
    parser.add_argument(
        "--force-autofigure",
        action="store_true",
        help="Fail instead of using fallback assets when AutoFigure-Edit is not configured.",
    )
    args = parser.parse_args()

    configure_fonts()
    _write_prompts(PROMPT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    if not _has_autofigure(args):
        if args.force_autofigure:
            raise SystemExit("AUTOFIGURE_EDIT_DIR and OPENAI_API_KEY are required with --force-autofigure.")
        print("AutoFigure-Edit is not configured; generating fallback SVG/PNG/PDF assets.")
        for spec in FIGURES:
            RENDERERS[spec.slug](spec, OUTPUT_DIR / spec.slug)
        return 0

    for spec in FIGURES:
        output_dir = OUTPUT_DIR / spec.slug
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        _run_autofigure(spec, args, output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
