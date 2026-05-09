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
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle


ROOT = Path(__file__).resolve().parent
PROMPT_DIR = ROOT / "figures" / "autofigure" / "prompts"
OUTPUT_DIR = ROOT / "figures" / "autofigure" / "outputs"
PDF_DIR = ROOT / "figures" / "autofigure" / "pdf"
CONTACT_SHEET = ROOT / "figures" / "autofigure" / "researcher_contact_sheet.png"
CACHED_AUTOFIGURE_DIR = Path.home() / ".cache" / "agent-firewall-tools" / "AutoFigure-Edit"

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
PAPER = "#fffaf0"
PAPER_EDGE = "#d8c3aa"
BROWN = "#7a5519"
GOLD = "#d7a84f"
GOLD_LIGHT = "#f8dfaa"
CYAN = "#d9f5f1"
CYAN_EDGE = "#62cfc8"
LANE_BLUE = "#eaf3ff"
LANE_GREEN = "#edf8e9"
LANE_PURPLE = "#f5ecfb"
LANE_YELLOW = "#fff5d8"
LANE_TEAL = "#e7f6f3"
LANE_RED = "#fff0ed"

STYLE_GUIDANCE = """Style requirements:
Use the uploaded or configured reference image style when available. The target visual language is Researcher/CycleResearcher-style academic process art: a warm paper background, large dashed outer frame, pastel dashed regions, thick tea-gold or gray arrows, compact editable icon cards, document stacks, database cylinders, shield/gate marks, review/score cards, and a larger role/icon block on the left of each lane. Keep it academic and clean, dense but readable, and do not use generic plain boxes only.
"""


@dataclass(frozen=True)
class FigureSpec:
    slug: str
    title: str
    prompt: str
    width: float = 10.8
    height: float = 5.25


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
        height=5.25,
    ),
    FigureSpec(
        slug="fig_proxy_pipeline",
        title="Proxy scan-only检测流水线",
        prompt="""Draw a horizontal flowchart in Chinese for the Proxy Service scan-only pipeline.
Nodes in order: parse 消息规范化, intent 攻击意图分类, rules denylist/长度/编码, scanners 本地扫描, decision 风险聚合, audit 请求日志.
From decision branch to ALLOW 继续Agent运行, MODIFY 脱敏/改写, BLOCK 暂停或拒绝.
Make clear that the proxy does not call the LLM and returns deterministic ALLOW/MODIFY/BLOCK decisions.""",
        height=5.05,
    ),
    FigureSpec(
        slug="fig_agent_pipeline",
        title="Agent Runtime运行图与工具安全边界",
        prompt="""Draw a Chinese thesis flow diagram for the Agent Runtime graph-compatible runner.
Main sequence: input 会话/清洗, intent 意图记录, policy 角色工具, router 工具规划, pre-tool gate RBAC/Schema/预算/确认, executor Internal/OpenClaw/MCP, post-tool gate PII/密钥/注入清洗, llm call Proxy预扫与模型响应, response 最终回复, memory/Trace.
Highlight three protected boundaries: before model call, before tool execution, after tool execution.
Use neutral academic styling and do not add unmentioned frameworks.""",
        width=10.8,
        height=5.25,
    ),
    FigureSpec(
        slug="fig_intervention_flow",
        title="Intervention人工审批闭环",
        prompt="""Draw a Chinese flowchart for the human intervention approval loop.
Flow: 暂停触发 from Proxy BLOCK or sensitive tool confirmation, 创建审批项 /v1/interventions status=pending, Approvals/Audit 本地控制台审核, approved path to Bridge worker 轮询approved并重放请求, Agent Runtime 验证审批状态, 完成并更新Trace.
Also show rejected path: 状态更新为 rejected, 原请求不执行真实敏感工具.
Keep arrows and labels clear for a thesis figure.""",
        height=5.05,
    ),
    FigureSpec(
        slug="fig_tool_gate_state_machine",
        title="工具调用门控状态机",
        prompt="""Draw a state-machine style Chinese diagram for tool-call gating in Agent-Firewall.
States: 工具计划生成, pre-tool检查, ALLOW, MODIFY, BLOCK, REQUIRE_CONFIRMATION, 审批通过重放, 工具执行, post-tool检查, PASS, REDACT, BLOCK_OUTPUT, Trace落盘, 最终回复.
Show that BLOCK and REQUIRE_CONFIRMATION stop execution before real tools, while REDACT/BLOCK_OUTPUT happen after tool execution before LLM context.
Use flowchart cards, guarded arrows, pastel swimlanes, and thesis-neutral terminology.""",
        height=5.25,
    ),
    FigureSpec(
        slug="fig_delegation",
        title="子Agent委派链的门控与审计",
        prompt="""Draw a Chinese schematic for sub-agent delegation governance.
Components: Main Agent receives task, Gate checks role/parameters/budget, Subagent/Tool from OpenClaw or MCP executes only if allowed, Trace records delegation evidence.
Call out risks: low-privilege user inducing high-privilege delegation, excessive context sent to sub-agent.
Call out control: delegation is modeled as an auditable protected tool call with quotas and post-tool cleaning.
Use concise thesis labels and no speculative entities.""",
        height=5.05,
    ),
    FigureSpec(
        slug="fig_trace_evidence",
        title="Trace审计证据链",
        prompt="""Draw a Chinese layered evidence-chain diagram for Agent-Firewall Trace.
Show sequential evidence blocks: 输入扫描 risk flags decision, 工具计划 tool name args, Pre gate RBAC Schema Confirm, Tool exec provider latency, Post gate redaction block, 最终回复.
Below them show a unified Trace/Audit store that records time, reason, result, sanitized preview, and cross-boundary decisions.
Make clear that Trace answers why a request was blocked, where it was blocked, whether a real tool executed, and whether raw output entered model context.""",
        height=5.05,
    ),
    FigureSpec(
        slug="fig_evidence_scope",
        title="实验口径与证据链总览",
        prompt="""Draw a Chinese overview diagram for thesis experimental evidence scope.
Left lane: 离线确定性复核, including pytest, mock LLM, static red-team scenarios, pure memory state, 11 agent-chain replay cases.
Right lane: 本机联调, including Telegram DM ingress, OpenClaw Gateway health, runtime contract, intervention approval, SQLite Trace/request/intervention evidence.
Bottom conclusion: two evidence types complement each other; no external benchmark numbers are mixed into deterministic conclusions.
Use a two-lane academic layout with clear boundaries and restrained colors.""",
        height=5.05,
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


def _default_autofigure_dir() -> str:
    configured = os.environ.get("AUTOFIGURE_EDIT_DIR", "")
    if configured:
        return configured
    if CACHED_AUTOFIGURE_DIR.exists():
        return str(CACHED_AUTOFIGURE_DIR)
    return ""


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


def _rf_canvas(spec: FigureSpec, *, title_size: float = 12.8):
    fig, ax = plt.subplots(figsize=(spec.width, spec.height), facecolor=PAPER)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax._rf_xscale = spec.height / spec.width  # compensate circle geometry in wide figure canvases
    ax.axis("off")
    ax.add_patch(Rectangle((0, 0), 1, 1, fc=PAPER, ec="none", zorder=-10))
    ax.text(0.5, 0.950, spec.title, fontsize=title_size, fontweight="bold", ha="center", va="top", color=INK)
    ax.add_patch(
        FancyBboxPatch(
            (0.025, 0.065),
            0.95,
            0.825,
            boxstyle="round,pad=0.004,rounding_size=0.006",
            fc="#fffdf8",
            ec="#888888",
            lw=1.35,
            linestyle=(0, (4.2, 3.2)),
        )
    )
    return fig, ax


def _rf_xscale(ax) -> float:
    return float(getattr(ax, "_rf_xscale", 1.0))


def _rf_circle(ax, cx: float, cy: float, r: float, **kwargs) -> None:
    ax.add_patch(Ellipse((cx, cy), 2 * r * _rf_xscale(ax), 2 * r, **kwargs))


def _rf_text(ax, x: float, y: float, text: str, size: float = 8.0, weight: str = "normal", color: str = INK, **kwargs) -> None:
    ax.text(x, y, text, fontsize=size, fontweight=weight, color=color, linespacing=1.08, **kwargs)


def _rf_panel(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    fc: str = "white",
    ec: str = "#9ca3af",
    lw: float = 1.0,
    dashed: bool = True,
    radius: float = 0.012,
    alpha: float = 1.0,
):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.006,rounding_size={radius}",
        fc=fc,
        ec=ec,
        lw=lw,
        linestyle=(0, (3, 2)) if dashed else "solid",
        alpha=alpha,
    )
    ax.add_patch(patch)
    return patch


def _rf_arrow(ax, start, end, *, color: str = "#9a9a9a", lw: float = 3.5, rad: float = 0.0, alpha: float = 0.92, scale: float = 18):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=scale,
            lw=lw,
            color=color,
            alpha=alpha,
            shrinkA=0,
            shrinkB=0,
            connectionstyle=f"arc3,rad={rad}",
        )
    )


def _rf_bracket(ax, x: float, y0: float, y1: float, label: str) -> None:
    ax.plot([x, x, x + 0.026], [y1, y0, y0], color=BROWN, lw=3.1, solid_capstyle="butt")
    ax.plot([x, x + 0.026], [y1, y1], color=BROWN, lw=3.1, solid_capstyle="butt")
    ax.text(x + 0.010, (y0 + y1) / 2, label, rotation=90, ha="center", va="center", fontsize=10.5, fontweight="bold", color=INK)


def _draw_doc(ax, x: float, y: float, w: float, h: float, *, fc: str = "#fffdf8", ec: str = LINE, lines: int = 3) -> None:
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=0.9))
    fold = min(w, h) * 0.22
    ax.add_patch(Polygon([[x + w - fold, y + h], [x + w, y + h], [x + w, y + h - fold]], closed=True, fc="#ece7dd", ec=ec, lw=0.55))
    for i in range(lines):
        yy = y + h * (0.73 - i * 0.18)
        ax.plot([x + w * 0.15, x + w * 0.83], [yy, yy], color="#8b8b8b", lw=0.7)


def _draw_doc_stack(ax, x: float, y: float, w: float, h: float, *, count: int = 3) -> None:
    for i in range(count):
        dx = i * w * 0.11
        dy = i * h * 0.07
        _draw_doc(ax, x + dx, y + dy, w * 0.70, h * 0.72, fc="#fffef8")
    ax.add_patch(Rectangle((x + w * 0.10, y + h * 0.38), w * 0.85, h * 0.16, fc=GOLD_LIGHT, ec="none", alpha=0.92))


def _draw_database(ax, x: float, y: float, w: float, h: float, *, fc: str = "#ead3b9") -> None:
    ax.add_patch(Rectangle((x, y + h * 0.16), w, h * 0.64, fc=fc, ec=PAPER_EDGE, lw=1.0))
    ax.add_patch(Ellipse((x + w / 2, y + h * 0.80), w, h * 0.26, fc=fc, ec=PAPER_EDGE, lw=1.0))
    ax.add_patch(Ellipse((x + w / 2, y + h * 0.16), w, h * 0.26, fc="#f4e5d2", ec=PAPER_EDGE, lw=1.0))
    _rf_circle(ax, x + w * 0.78, y + h * 0.18, w * 0.16, fc="#f8fafc", ec=PAPER_EDGE, lw=0.9)
    ax.plot([x + w * 0.88, x + w * 1.02], [y + h * 0.08, y - h * 0.04], color=PAPER_EDGE, lw=1.3)


def _draw_robot(ax, x: float, y: float, w: float, h: float, *, accent: str = "#8bd3dd", tool: str = "laptop") -> None:
    _rf_circle(ax, x + w * 0.34, y + h * 0.58, w * 0.19, fc="#edf2f7", ec=LINE, lw=1.0)
    ax.add_patch(FancyBboxPatch((x + w * 0.23, y + h * 0.52), w * 0.22, h * 0.09, boxstyle="round,pad=0.002,rounding_size=0.018", fc="#253043", ec=LINE, lw=0.7))
    _rf_circle(ax, x + w * 0.29, y + h * 0.565, w * 0.027, fc=accent, ec="none")
    _rf_circle(ax, x + w * 0.39, y + h * 0.565, w * 0.027, fc=accent, ec="none")
    ax.add_patch(Rectangle((x + w * 0.24, y + h * 0.20), w * 0.22, h * 0.21, fc="#f8fafc", ec=LINE, lw=0.9))
    ax.add_patch(Rectangle((x + w * 0.18, y + h * 0.14), w * 0.34, h * 0.055, fc=BROWN, ec=LINE, lw=0.65))
    if tool == "laptop":
        ax.add_patch(Rectangle((x + w * 0.54, y + h * 0.24), w * 0.22, h * 0.15, fc="#e8f0ff", ec=LINE, lw=0.8))
        ax.add_patch(Rectangle((x + w * 0.52, y + h * 0.20), w * 0.27, h * 0.035, fc="#c8ccd4", ec=LINE, lw=0.55))
    elif tool == "shield":
        _draw_shield(ax, x + w * 0.56, y + h * 0.25, w * 0.20, h * 0.22, fc="#fff7cc")
    elif tool == "trace":
        _draw_chart(ax, x + w * 0.55, y + h * 0.25, w * 0.22, h * 0.20)
    else:
        _draw_tool(ax, x + w * 0.55, y + h * 0.26, w * 0.22, h * 0.18)


def _draw_shield(ax, x: float, y: float, w: float, h: float, *, fc: str = "#fff3c4", ec: str = LINE) -> None:
    pts = [[x + w * 0.50, y + h], [x + w * 0.88, y + h * 0.82], [x + w * 0.78, y + h * 0.30], [x + w * 0.50, y], [x + w * 0.22, y + h * 0.30], [x + w * 0.12, y + h * 0.82]]
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=0.9))
    ax.plot([x + w * 0.31, x + w * 0.45, x + w * 0.72], [y + h * 0.55, y + h * 0.36, y + h * 0.67], color="#17935b", lw=1.6)


def _draw_stop(ax, x: float, y: float, w: float, h: float) -> None:
    _rf_circle(ax, x + w / 2, y + h / 2, min(w, h) * 0.38, fc="#ffd5d0", ec="#bf2e2e", lw=1.0)
    ax.plot([x + w * 0.34, x + w * 0.66], [y + h * 0.34, y + h * 0.66], color="#bf2e2e", lw=1.5)
    ax.plot([x + w * 0.66, x + w * 0.34], [y + h * 0.34, y + h * 0.66], color="#bf2e2e", lw=1.5)


def _draw_folder(ax, x: float, y: float, w: float, h: float) -> None:
    ax.add_patch(Rectangle((x, y), w, h * 0.70, fc="#ffd84d", ec=LINE, lw=0.9))
    ax.add_patch(Rectangle((x + w * 0.05, y + h * 0.60), w * 0.32, h * 0.18, fc="#ffe98d", ec=LINE, lw=0.7))
    ax.plot([x + w * 0.10, x + w * 0.84], [y + h * 0.42, y + h * 0.42], color="#a16207", lw=1.0)


def _draw_tool(ax, x: float, y: float, w: float, h: float) -> None:
    _draw_folder(ax, x, y + h * 0.08, w * 0.70, h * 0.70)
    ax.plot([x + w * 0.68, x + w * 0.92], [y + h * 0.20, y + h * 0.78], color=LINE, lw=2.0)
    _rf_circle(ax, x + w * 0.92, y + h * 0.80, w * 0.08, fc="#e2e8f0", ec=LINE, lw=0.8)


def _draw_chart(ax, x: float, y: float, w: float, h: float) -> None:
    ax.add_patch(Rectangle((x, y), w, h, fc="#eff6ff", ec=LINE, lw=0.9))
    ax.plot([x + w * 0.12, x + w * 0.28, x + w * 0.48, x + w * 0.70, x + w * 0.88], [y + h * 0.25, y + h * 0.52, y + h * 0.41, y + h * 0.70, y + h * 0.58], color="#2563eb", lw=1.8)
    for i, c in enumerate(["#60a5fa", "#f59e0b", "#22c55e"]):
        ax.add_patch(Rectangle((x + w * (0.18 + i * 0.20), y + h * 0.08), w * 0.09, h * (0.25 + i * 0.10), fc=c, ec="none", alpha=0.78))


def _draw_clipboard(ax, x: float, y: float, w: float, h: float) -> None:
    ax.add_patch(Rectangle((x + w * 0.10, y), w * 0.80, h * 0.90, fc="#fffdf5", ec=LINE, lw=0.9))
    ax.add_patch(Rectangle((x + w * 0.34, y + h * 0.82), w * 0.32, h * 0.16, fc=GOLD_LIGHT, ec=LINE, lw=0.7))
    for i in range(3):
        yy = y + h * (0.63 - i * 0.20)
        ax.plot([x + w * 0.25, x + w * 0.75], [yy, yy], color="#9ca3af", lw=0.8)
    ax.plot([x + w * 0.25, x + w * 0.36, x + w * 0.56], [y + h * 0.24, y + h * 0.12, y + h * 0.34], color="#16a34a", lw=1.7)


def _draw_score(ax, x: float, y: float, w: float, h: float) -> None:
    ax.add_patch(Rectangle((x, y), w, h, fc="#fffdf8", ec=LINE, lw=0.9))
    ax.text(x + w * 0.50, y + h * 0.68, "7/10", fontsize=7.5, ha="center", va="center", fontweight="bold", color=INK)
    ax.add_patch(Rectangle((x + w * 0.16, y + h * 0.18), w * 0.68, h * 0.17, fc="#fee2e2", ec="none"))
    ax.text(x + w * 0.50, y + h * 0.26, "Decision", fontsize=5.2, ha="center", va="center", color="#991b1b")


def _draw_brain(ax, x: float, y: float, w: float, h: float) -> None:
    _rf_circle(ax, x + w * 0.42, y + h * 0.58, w * 0.18, fc="#fed7aa", ec=LINE, lw=0.8)
    _rf_circle(ax, x + w * 0.58, y + h * 0.58, w * 0.18, fc="#fed7aa", ec=LINE, lw=0.8)
    _rf_circle(ax, x + w * 0.50, y + h * 0.40, w * 0.20, fc="#fdba74", ec=LINE, lw=0.8)
    for dx in [0.35, 0.50, 0.65]:
        ax.plot([x + w * dx, x + w * dx], [y + h * 0.12, y + h * 0.25], color=LINE, lw=0.8)


def _draw_icon(ax, kind: str, x: float, y: float, w: float, h: float) -> None:
    if kind in {"doc", "message", "paper"}:
        _draw_doc_stack(ax, x + w * 0.08, y + h * 0.08, w * 0.85, h * 0.82, count=2 if kind == "message" else 3)
    elif kind in {"db", "memory", "sqlite"}:
        _draw_database(ax, x + w * 0.18, y + h * 0.12, w * 0.62, h * 0.75)
    elif kind in {"gate", "shield", "rbac"}:
        _draw_shield(ax, x + w * 0.18, y + h * 0.12, w * 0.64, h * 0.78)
    elif kind in {"tool", "provider", "openclaw"}:
        _draw_tool(ax, x + w * 0.14, y + h * 0.12, w * 0.78, h * 0.76)
    elif kind in {"trace", "chart", "audit"}:
        _draw_chart(ax, x + w * 0.14, y + h * 0.15, w * 0.72, h * 0.70)
    elif kind in {"approve", "approval", "clipboard"}:
        _draw_clipboard(ax, x + w * 0.17, y + h * 0.10, w * 0.66, h * 0.78)
    elif kind in {"block", "risk", "stop"}:
        _draw_stop(ax, x + w * 0.18, y + h * 0.12, w * 0.64, h * 0.75)
    elif kind in {"llm", "brain"}:
        _draw_brain(ax, x + w * 0.12, y + h * 0.10, w * 0.76, h * 0.80)
    elif kind == "score":
        _draw_score(ax, x + w * 0.18, y + h * 0.12, w * 0.64, h * 0.78)
    elif kind == "folder":
        _draw_folder(ax, x + w * 0.15, y + h * 0.20, w * 0.72, h * 0.62)
    else:
        _draw_doc(ax, x + w * 0.22, y + h * 0.12, w * 0.56, h * 0.76)


def _rf_node(ax, x: float, y: float, w: float, h: float, label: str, icon: str, *, edge: str = "#6b83c6", fill: str = "#fffdf8", fs: float = 7.0):
    _rf_panel(ax, x, y, w, h, fc=fill, ec=edge, lw=0.95, dashed=True, radius=0.008)
    _draw_icon(ax, icon, x + w * 0.10, y + h * 0.40, w * 0.80, h * 0.54)
    _rf_text(ax, x + w / 2, y + h * 0.22, label, size=fs, weight="bold", ha="center", va="center")


def _rf_role(ax, x: float, y: float, w: float, h: float, label: str, *, accent: str, tool: str) -> None:
    _rf_panel(ax, x, y, w, h, fc="white", ec="#6b83c6", lw=1.0, dashed=True, radius=0.010)
    _draw_robot(ax, x + w * 0.08, y + h * 0.17, w * 0.66, h * 0.68, accent=accent, tool=tool)
    if label:
        _rf_text(ax, x + w * 0.50, y + h * 0.09, label, size=6.4, weight="bold", ha="center", va="center", color=BROWN)


def _rf_lane(ax, y: float, h: float, title: str, color: str, role_label: str, role_tool: str, nodes: list[tuple[str, str]], *, footer=None) -> None:
    _rf_panel(ax, 0.055, y, 0.89, h, fc=color, ec="#7e8aa2", lw=1.0, dashed=True, radius=0.014, alpha=0.92)
    _rf_text(ax, 0.50, y + h - 0.016, title, size=7.4, weight="bold", ha="center", va="top", color=BROWN if "Step" in title else INK)
    _rf_role(ax, 0.075, y + h * 0.18, 0.115, h * 0.60, role_label, accent="#6ee7f9", tool=role_tool)

    n = len(nodes)
    x0, x1 = 0.245, 0.920
    gap = 0.022 if n >= 6 else 0.030
    node_w = min(0.098 if n >= 6 else 0.112, (x1 - x0 - gap * (n - 1)) / n)
    total = node_w * n + gap * (n - 1)
    start = x0 + (x1 - x0 - total) / 2
    node_h = h * 0.45
    node_y = y + h * 0.205
    _rf_arrow(ax, (0.192, y + h * 0.49), (start - 0.010, node_y + node_h * 0.50), lw=3.8, color="#aaa7a2")
    for i, (label, icon) in enumerate(nodes):
        x = start + i * (node_w + gap)
        _rf_node(ax, x, node_y, node_w, node_h, label, icon, fs=6.3 if n >= 6 else 6.9)
        if i > 0:
            prev = start + (i - 1) * (node_w + gap)
            _rf_arrow(ax, (prev + node_w + 0.004, node_y + node_h * 0.50), (x - 0.006, node_y + node_h * 0.50), lw=2.8, color="#aaa7a2", scale=14)
    if footer:
        _rf_text(ax, 0.50, y + 0.020, footer, size=6.4, ha="center", va="bottom", color=MUTED)


def _rf_status_chip(ax, x: float, y: float, text: str, fc: str, ec=None) -> None:
    _rf_panel(ax, x, y, 0.086, 0.050, fc=fc, ec=ec or "#9ca3af", lw=0.8, dashed=False, radius=0.008)
    _rf_text(ax, x + 0.043, y + 0.025, text, size=6.2, weight="bold", ha="center", va="center", color=INK)


def _rf_footer(ax, text: str) -> None:
    _rf_text(ax, 0.5, 0.085, text, size=8.4, weight="bold", ha="center", va="center", color="#64748b")


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


def _render_trust_boundaries_researcher(spec: FigureSpec, output_dir: Path) -> None:
    fig, ax = _rf_canvas(spec)
    _rf_bracket(ax, 0.038, 0.16, 0.82, "Trust Boundaries")
    _rf_panel(ax, 0.075, 0.67, 0.84, 0.16, fc=LANE_BLUE, ec="#8b9bb5", lw=1.0, dashed=True)
    _rf_text(ax, 0.095, 0.797, "外部输入域", size=9.6, weight="bold", color=BROWN, ha="left", va="center")
    _rf_panel(ax, 0.075, 0.42, 0.84, 0.17, fc=LANE_GREEN, ec="#8b9bb5", lw=1.0, dashed=True)
    _rf_text(ax, 0.095, 0.555, "受保护运行域", size=9.6, weight="bold", color=BROWN, ha="left", va="center")
    _rf_panel(ax, 0.075, 0.17, 0.84, 0.17, fc=LANE_PURPLE, ec="#8b9bb5", lw=1.0, dashed=True)
    _rf_text(ax, 0.095, 0.305, "工具与证据域", size=9.6, weight="bold", color=BROWN, ha="left", va="center")

    flow = [
        (0.145, 0.690, "外部\n消息", "message"),
        (0.305, 0.690, "入口\n适配器", "doc"),
        (0.465, 0.440, "Proxy\n/v1/scan", "shield"),
        (0.625, 0.440, "Agent Runtime\n工具计划", "brain"),
        (0.785, 0.190, "OpenClaw/MCP\n工具输出", "tool"),
    ]
    for x, y, label, icon in flow:
        _rf_node(ax, x, y, 0.105, 0.105, label, icon, fs=6.5)
    _rf_arrow(ax, (0.250, 0.742), (0.305, 0.742), color=GOLD, lw=3.4)
    _rf_arrow(ax, (0.410, 0.725), (0.465, 0.540), color=GOLD, lw=3.4, rad=-0.18)
    _rf_arrow(ax, (0.570, 0.492), (0.625, 0.492), color=GOLD, lw=3.4)
    _rf_arrow(ax, (0.730, 0.460), (0.785, 0.290), color=GOLD, lw=3.4, rad=-0.18)

    for x in [0.405, 0.585, 0.745]:
        ax.plot([x, x], [0.165, 0.825], color="#c2410c", lw=1.5, linestyle=(0, (5, 3)), alpha=0.75)
    notes = [
        (0.332, 0.606, "边界1\n消息进入运行时"),
        (0.525, 0.606, "边界2\n模型计划到真实工具"),
        (0.695, 0.356, "边界3\n工具结果回流上下文"),
    ]
    for x, y, text in notes:
        _rf_panel(ax, x, y, 0.128, 0.068, fc="#fffdf8", ec="#c2410c", lw=0.9, dashed=True, radius=0.008)
        _rf_text(ax, x + 0.064, y + 0.034, text, size=6.3, weight="bold", ha="center", va="center", color="#9a3412")

    _rf_node(ax, 0.805, 0.430, 0.090, 0.095, "Trace\n审计", "trace", fs=6.4)
    _rf_arrow(ax, (0.730, 0.492), (0.805, 0.477), color="#aaa7a2", lw=2.8)
    _rf_footer(ax, "跨边界动作由 Proxy、pre-tool gate、post-tool gate 与 Trace 共同证明，而不是依赖自然语言承诺。")
    _save_fallback(fig, output_dir)


def _render_architecture_researcher(spec: FigureSpec, output_dir: Path) -> None:
    fig, ax = _rf_canvas(spec, title_size=13.2)
    _rf_panel(ax, 0.085, 0.805, 0.350, 0.080, fc="#fffdf8", ec=PAPER_EDGE, lw=1.0, dashed=False, radius=0.010)
    _draw_database(ax, 0.105, 0.818, 0.045, 0.050)
    _rf_text(ax, 0.165, 0.846, "tool catalog / runtime spec", size=8.4, weight="bold", color=INK, ha="left", va="center")
    _draw_doc_stack(ax, 0.335, 0.812, 0.080, 0.055, count=4)
    _rf_bracket(ax, 0.045, 0.180, 0.775, "Runtime Loop")

    _rf_panel(ax, 0.085, 0.580, 0.835, 0.185, fc=LANE_BLUE, ec="#8a8a8a", lw=1.1, dashed=True)
    _rf_text(ax, 0.105, 0.730, "Ingress", size=12, weight="bold", color=BROWN, ha="left", va="center")
    _rf_role(ax, 0.105, 0.610, 0.130, 0.115, "入口适配", accent="#7dd3fc", tool="laptop")
    top_nodes = [
        (0.285, "Telegram\nBridge", "message"),
        (0.425, "Agent Runtime\n:8002", "brain"),
        (0.565, "Proxy\n/v1/scan", "shield"),
        (0.705, "Tool Plan\nRBAC/Schema", "gate"),
        (0.845, "回复\n通道", "doc"),
    ]
    for x, label, icon in top_nodes:
        _rf_node(ax, x, 0.625, 0.096, 0.095, label, icon, fs=6.3)
    for sx, ex in [(0.235, 0.285), (0.381, 0.425), (0.521, 0.565), (0.661, 0.705), (0.801, 0.845)]:
        _rf_arrow(ax, (sx, 0.672), (ex, 0.672), color=GOLD, lw=3.2)

    _rf_panel(ax, 0.085, 0.185, 0.390, 0.290, fc=LANE_YELLOW, ec="#8a8a8a", lw=1.1, dashed=True)
    _rf_text(ax, 0.105, 0.435, "Evidence", size=12, weight="bold", color=BROWN, ha="left", va="center")
    _rf_role(ax, 0.110, 0.275, 0.120, 0.115, "审计视图", accent="#a7f3d0", tool="trace")
    _rf_node(ax, 0.275, 0.300, 0.095, 0.090, "SQLite\nmemory", "db", fs=6.2)
    _rf_node(ax, 0.390, 0.300, 0.065, 0.090, "Trace\nAudit", "trace", fs=6.1)

    _rf_panel(ax, 0.495, 0.185, 0.425, 0.290, fc=LANE_GREEN, ec="#8a8a8a", lw=1.1, dashed=True)
    _rf_text(ax, 0.515, 0.435, "Protected Tools", size=12, weight="bold", color=BROWN, ha="left", va="center")
    _rf_node(ax, 0.540, 0.300, 0.100, 0.092, "pre-tool\ngate", "shield", fs=6.2)
    _rf_node(ax, 0.672, 0.300, 0.110, 0.092, "OpenClaw/MCP\nRuntime", "tool", fs=6.0)
    _rf_node(ax, 0.815, 0.300, 0.085, 0.092, "post-tool\nredaction", "gate", fs=5.9)
    _rf_arrow(ax, (0.640, 0.346), (0.672, 0.346), color=GOLD, lw=2.9)
    _rf_arrow(ax, (0.782, 0.346), (0.815, 0.346), color=GOLD, lw=2.9)
    _rf_arrow(ax, (0.754, 0.625), (0.590, 0.392), color="#9b9b9b", lw=3.0, rad=0.05)
    _rf_arrow(ax, (0.855, 0.300), (0.420, 0.330), color="#9b9b9b", lw=2.8, rad=-0.18)

    _rf_panel(ax, 0.530, 0.800, 0.340, 0.065, fc="#fffdf8", ec=PAPER_EDGE, lw=0.9, dashed=False, radius=0.008)
    _draw_chart(ax, 0.548, 0.812, 0.050, 0.038)
    _rf_text(ax, 0.615, 0.832, "Nuxt/Vuetify Control Plane", size=8.0, weight="bold", ha="left", va="center", color=BROWN)
    _rf_arrow(ax, (0.700, 0.800), (0.615, 0.720), color="#9b9b9b", lw=2.7, rad=0.18)
    _rf_footer(ax, "Agent-Firewall 包裹 OpenClaw 工具执行；Telegram 只是入口适配器之一。")
    _save_fallback(fig, output_dir)


def _render_proxy_pipeline_researcher(spec: FigureSpec, output_dir: Path) -> None:
    fig, ax = _rf_canvas(spec)
    lanes = [
        ("Step 1: scan-only 输入检测", LANE_BLUE, "扫描入口", "laptop", [("parse\n规范化", "doc"), ("intent\n意图", "trace"), ("rules\n规则", "shield"), ("scanners\n本地扫描", "gate"), ("risk\n聚合", "score"), ("audit\n日志", "trace")]),
        ("Step 2: 确定性决策输出", LANE_GREEN, "门控输出", "shield", [("ALLOW\n继续", "shield"), ("MODIFY\n清洗", "approve"), ("BLOCK\n暂停", "block"), ("intervention\n审批", "clipboard")]),
        ("Step 3: 审计与复核", LANE_YELLOW, "证据回收", "trace", [("request\nlog", "doc"), ("risk flags\n记录", "trace"), ("sanitized\npreview", "message"), ("Trace/Audit\n页面", "chart")]),
    ]
    y0 = [0.650, 0.405, 0.160]
    for (title, color, role, tool, nodes), y in zip(lanes, y0):
        _rf_lane(ax, y, 0.190, title, color, role, tool, nodes)
    _rf_arrow(ax, (0.720, 0.650), (0.695, 0.595), color="#9b9b9b", lw=3.0, rad=0.1)
    _rf_arrow(ax, (0.710, 0.405), (0.690, 0.350), color="#9b9b9b", lw=3.0, rad=0.1)
    _rf_footer(ax, "Proxy 不调用 LLM，只返回 ALLOW / MODIFY / BLOCK 和可审计风险原因。")
    _save_fallback(fig, output_dir)


def _render_agent_pipeline_researcher(spec: FigureSpec, output_dir: Path) -> None:
    fig, ax = _rf_canvas(spec)
    lanes = [
        ("Step 1: Agent Runtime 会话与规划", LANE_BLUE, "运行图入口", "laptop", [("input\n会话/清洗", "message"), ("intent\n记录", "trace"), ("policy\n角色工具", "shield"), ("router\n工具规划", "brain"), ("Proxy\n预扫", "gate")]),
        ("Step 2: 工具执行安全边界", LANE_GREEN, "工具门控", "shield", [("pre-tool\nRBAC/Schema", "shield"), ("budget\n限额", "score"), ("executor\nInternal/OpenClaw/MCP", "tool"), ("post-tool\nPII/密钥清洗", "gate")]),
        ("Step 3: 模型响应与证据链", LANE_PURPLE, "证据追踪", "trace", [("LLM call\n响应", "brain"), ("response\n最终回复", "doc"), ("memory\n会话", "db"), ("Trace\n落盘", "trace")]),
    ]
    for lane, y in zip(lanes, [0.650, 0.405, 0.160]):
        _rf_lane(ax, y, 0.190, *lane)
    ax.text(0.250, 0.352, "Boundary A\n模型调用前", fontsize=6.0, color="#9a3412", ha="center", va="center", fontweight="bold")
    ax.text(0.512, 0.352, "Boundary B\n真实工具前", fontsize=6.0, color="#9a3412", ha="center", va="center", fontweight="bold")
    ax.text(0.750, 0.352, "Boundary C\n结果入上下文前", fontsize=6.0, color="#9a3412", ha="center", va="center", fontweight="bold")
    for x in [0.250, 0.512, 0.750]:
        ax.plot([x, x], [0.165, 0.835], color="#c2410c", lw=1.2, linestyle=(0, (4, 3)), alpha=0.45)
    _rf_arrow(ax, (0.805, 0.650), (0.810, 0.595), color="#9b9b9b", lw=3.0)
    _rf_arrow(ax, (0.810, 0.405), (0.805, 0.350), color="#9b9b9b", lw=3.0)
    _rf_footer(ax, "运行图保留 graph-compatible 语义，但每个副作用边界由后端门控与 Trace 证明。")
    _save_fallback(fig, output_dir)


def _render_intervention_flow_researcher(spec: FigureSpec, output_dir: Path) -> None:
    fig, ax = _rf_canvas(spec)
    _rf_panel(ax, 0.065, 0.600, 0.855, 0.215, fc=LANE_GREEN, ec="#8a8a8a", lw=1.1, dashed=True)
    _rf_text(ax, 0.090, 0.775, "Approved path", size=11.0, weight="bold", color=BROWN, ha="left", va="center")
    approved = [("暂停\n触发", "block"), ("pending\n审批项", "doc"), ("控制台\n审核", "approve"), ("Bridge\n重放", "tool"), ("Agent Runtime\n验证审批", "shield"), ("完成\nTrace", "trace")]
    xs = [0.145, 0.285, 0.425, 0.565, 0.705, 0.845]
    for x, (label, icon) in zip(xs, approved):
        _rf_node(ax, x, 0.645, 0.090, 0.092, label, icon, fs=6.1)
    for a, b in zip(xs, xs[1:]):
        _rf_arrow(ax, (a + 0.090, 0.691), (b - 0.006, 0.691), color=GOLD, lw=2.9, scale=14)

    _rf_panel(ax, 0.065, 0.280, 0.855, 0.225, fc=LANE_RED, ec="#8a8a8a", lw=1.1, dashed=True)
    _rf_text(ax, 0.090, 0.462, "Rejected path", size=11.0, weight="bold", color="#991b1b", ha="left", va="center")
    rejected = [("本地\n拒绝", "block"), ("status\nrejected", "doc"), ("原请求\n终止", "stop"), ("真实工具\n不执行", "tool"), ("Trace\n记录", "trace")]
    xs2 = [0.190, 0.335, 0.480, 0.625, 0.770]
    for x, (label, icon) in zip(xs2, rejected):
        _rf_node(ax, x, 0.325, 0.090, 0.092, label, icon, edge="#d36b5c", fs=6.1)
    for a, b in zip(xs2, xs2[1:]):
        _rf_arrow(ax, (a + 0.090, 0.371), (b - 0.006, 0.371), color="#d36b5c", lw=2.8, scale=14)

    _rf_arrow(ax, (0.425, 0.645), (0.335, 0.417), color="#9b9b9b", lw=2.8, rad=0.22)
    _rf_panel(ax, 0.390, 0.155, 0.230, 0.065, fc="#fffdf8", ec=PAPER_EDGE, lw=0.9, dashed=False, radius=0.010)
    _rf_text(ax, 0.505, 0.188, "approved_intervention_id 是恢复执行的唯一凭据", size=7.0, weight="bold", color=BROWN, ha="center", va="center")
    _rf_footer(ax, "审批通过才重放请求；拒绝路径不会执行高敏或被阻断的真实工具。")
    _save_fallback(fig, output_dir)


def _render_tool_gate_state_machine_researcher(spec: FigureSpec, output_dir: Path) -> None:
    fig, ax = _rf_canvas(spec)
    _rf_panel(ax, 0.060, 0.630, 0.860, 0.200, fc=LANE_BLUE, ec="#8a8a8a", lw=1.1, dashed=True)
    _rf_text(ax, 0.085, 0.790, "Pre-tool decision", size=11, weight="bold", color=BROWN, ha="left", va="center")
    top = [(0.135, "工具计划\n生成", "doc"), (0.300, "pre-tool\n检查", "shield"), (0.470, "ALLOW\nMODIFY", "approve"), (0.640, "BLOCK\nCONFIRM", "block")]
    for x, label, icon in top:
        _rf_node(ax, x, 0.675, 0.105, 0.095, label, icon, fs=6.2)
    for a, b in [(0.240, 0.300), (0.405, 0.470), (0.575, 0.640)]:
        _rf_arrow(ax, (a, 0.722), (b - 0.006, 0.722), color=GOLD, lw=2.9)

    _rf_panel(ax, 0.060, 0.395, 0.860, 0.155, fc=LANE_YELLOW, ec="#8a8a8a", lw=1.1, dashed=True)
    _rf_text(ax, 0.085, 0.513, "Execution after approval", size=11, weight="bold", color=BROWN, ha="left", va="center")
    mid = [(0.310, "审批通过\n重放", "approve"), (0.485, "真实工具\n执行", "tool"), (0.660, "工具结果\n返回", "doc")]
    for x, label, icon in mid:
        _rf_node(ax, x, 0.425, 0.105, 0.085, label, icon, fs=6.2)
    for a, b in [(0.415, 0.485), (0.590, 0.660)]:
        _rf_arrow(ax, (a, 0.467), (b - 0.006, 0.467), color=GOLD, lw=2.9)

    _rf_panel(ax, 0.060, 0.160, 0.860, 0.155, fc=LANE_PURPLE, ec="#8a8a8a", lw=1.1, dashed=True)
    _rf_text(ax, 0.085, 0.278, "Post-tool decision", size=11, weight="bold", color=BROWN, ha="left", va="center")
    bot = [(0.170, "post-tool\n检查", "shield"), (0.335, "PASS\nREDACT", "approve"), (0.500, "BLOCK\nOUTPUT", "block"), (0.665, "Trace\n落盘", "trace"), (0.815, "最终\n回复", "doc")]
    for x, label, icon in bot:
        _rf_node(ax, x, 0.190, 0.095, 0.085, label, icon, fs=6.0)
    for a, b in [(0.265, 0.335), (0.430, 0.500), (0.595, 0.665), (0.760, 0.815)]:
        _rf_arrow(ax, (a, 0.232), (b - 0.006, 0.232), color=GOLD, lw=2.8, scale=14)

    _rf_arrow(ax, (0.705, 0.675), (0.360, 0.510), color="#a0a0a0", lw=3.0, rad=0.18)
    _rf_arrow(ax, (0.713, 0.425), (0.218, 0.275), color="#a0a0a0", lw=3.0, rad=0.18)
    _rf_arrow(ax, (0.690, 0.675), (0.500, 0.275), color="#d36b5c", lw=2.7, rad=-0.18)
    _rf_footer(ax, "BLOCK/CONFIRM 在真实工具前停止；REDACT/BLOCK_OUTPUT 在工具结果进入模型上下文前停止。")
    _save_fallback(fig, output_dir)


def _render_delegation_researcher(spec: FigureSpec, output_dir: Path) -> None:
    fig, ax = _rf_canvas(spec)
    _rf_panel(ax, 0.070, 0.600, 0.850, 0.210, fc=LANE_BLUE, ec="#8a8a8a", lw=1.1, dashed=True)
    _rf_text(ax, 0.095, 0.772, "Delegation as protected tool call", size=11, weight="bold", color=BROWN, ha="left", va="center")
    main = [(0.165, "Main Agent\n任务", "brain"), (0.330, "Gate\n角色/预算", "shield"), (0.505, "Subagent/Tool\nOpenClaw/MCP", "tool"), (0.710, "Trace\n证据链", "trace")]
    for x, label, icon in main:
        _rf_node(ax, x, 0.645, 0.115, 0.095, label, icon, fs=6.1)
    for a, b in [(0.280, 0.330), (0.445, 0.505), (0.620, 0.710)]:
        _rf_arrow(ax, (a, 0.692), (b - 0.006, 0.692), color=GOLD, lw=3.0)

    _rf_panel(ax, 0.070, 0.355, 0.400, 0.155, fc=LANE_RED, ec="#8a8a8a", lw=1.1, dashed=True)
    _rf_text(ax, 0.095, 0.475, "Risks", size=10.5, weight="bold", color="#991b1b", ha="left", va="center")
    _rf_node(ax, 0.145, 0.385, 0.100, 0.080, "低权限\n高权限代办", "risk", edge="#d36b5c", fs=5.9)
    _rf_node(ax, 0.295, 0.385, 0.100, 0.080, "过量\n上下文", "risk", edge="#d36b5c", fs=5.9)

    _rf_panel(ax, 0.520, 0.355, 0.400, 0.155, fc=LANE_GREEN, ec="#8a8a8a", lw=1.1, dashed=True)
    _rf_text(ax, 0.545, 0.475, "Controls", size=10.5, weight="bold", color=BROWN, ha="left", va="center")
    _rf_node(ax, 0.585, 0.385, 0.085, 0.080, "RBAC\n校验", "shield", fs=5.9)
    _rf_node(ax, 0.705, 0.385, 0.085, 0.080, "限额\n控制", "score", fs=5.9)
    _rf_node(ax, 0.825, 0.385, 0.070, 0.080, "输出\n清洗", "gate", fs=5.7)

    _rf_panel(ax, 0.230, 0.165, 0.540, 0.075, fc="#fffdf8", ec=PAPER_EDGE, lw=0.9, dashed=False, radius=0.010)
    _rf_text(ax, 0.500, 0.203, "委派不绕过防火墙，而是进入同一套工具调用门控与 Trace 体系。", size=7.5, weight="bold", color=BROWN, ha="center", va="center")
    _rf_arrow(ax, (0.250, 0.645), (0.195, 0.465), color="#d36b5c", lw=2.8, rad=-0.15)
    _rf_arrow(ax, (0.765, 0.645), (0.750, 0.465), color="#8a8a8a", lw=2.8, rad=0.15)
    _rf_footer(ax, "子Agent委派按受保护工具流建模：角色、参数、预算、输出清洗和证据记录缺一不可。")
    _save_fallback(fig, output_dir)


def _render_trace_evidence_researcher(spec: FigureSpec, output_dir: Path) -> None:
    fig, ax = _rf_canvas(spec)
    _rf_panel(ax, 0.055, 0.160, 0.240, 0.650, fc="#fffdf8", ec="#d1d5db", lw=1.2, dashed=False, radius=0.018)
    _rf_text(ax, 0.070, 0.780, "a) Runtime Input", size=10.5, weight="bold", ha="left", va="center")
    _rf_node(ax, 0.090, 0.650, 0.085, 0.085, "用户\n消息", "message", fs=5.9)
    _rf_node(ax, 0.190, 0.650, 0.075, 0.085, "工具\n计划", "doc", fs=5.9)
    _rf_arrow(ax, (0.175, 0.692), (0.190, 0.692), color="#9b9b9b", lw=2.5, scale=12)
    for i, t in enumerate(["Proxy: risk flags", "Pre gate: RBAC/Schema", "Tool exec: provider latency", "Post gate: redaction/block"]):
        _rf_panel(ax, 0.085, 0.545 - i * 0.075, 0.165, 0.044, fc="#f8fafc", ec="#cbd5e1", lw=0.7, dashed=False, radius=0.006)
        _rf_text(ax, 0.167, 0.567 - i * 0.075, t, size=5.8, ha="center", va="center", color=INK)

    _rf_panel(ax, 0.320, 0.160, 0.625, 0.650, fc="#eef9f6", ec="#d1d5db", lw=1.2, dashed=False, radius=0.018)
    _rf_text(ax, 0.340, 0.780, "b) Trace Evidence Output", size=10.5, weight="bold", ha="left", va="center")
    stages = [
        ("z1 输入扫描", "risk score / decision / matched rule", LANE_BLUE),
        ("z2 工具门控", "tool name / args / RBAC / confirmation", LANE_GREEN),
        ("z3 输出清洗", "redaction / block_output / sanitized preview", LANE_TEAL),
        ("(s,a) 审计结论", "why blocked / where blocked / real tool executed?", LANE_YELLOW),
    ]
    y = 0.670
    for idx, (head, body, color) in enumerate(stages):
        _rf_panel(ax, 0.345, y - idx * 0.130, 0.560, 0.095, fc=color, ec=CYAN_EDGE, lw=1.0, dashed=False, radius=0.010)
        _rf_text(ax, 0.365, y + 0.058 - idx * 0.130, head, size=8.4, weight="bold", color=BROWN, ha="left", va="center")
        _rf_text(ax, 0.535, y + 0.058 - idx * 0.130, body, size=6.5, color=INK, ha="left", va="center")
        _draw_icon(ax, ["shield", "gate", "trace", "score"][idx], 0.825, y + 0.012 - idx * 0.130, 0.055, 0.055)
        if idx < len(stages) - 1:
            _rf_arrow(ax, (0.625, y - 0.005 - idx * 0.130), (0.625, y - 0.035 - idx * 0.130), color="#22b8c7", lw=2.6, scale=12)
    _rf_footer(ax, "Trace 将输入扫描、工具计划、前置门控、工具执行、后置清洗和最终回复串成可复核证据链。")
    _save_fallback(fig, output_dir)


def _render_evidence_scope_researcher(spec: FigureSpec, output_dir: Path) -> None:
    fig, ax = _rf_canvas(spec)
    _rf_panel(ax, 0.065, 0.220, 0.395, 0.565, fc=LANE_BLUE, ec="#8a8a8a", lw=1.1, dashed=True)
    _rf_text(ax, 0.090, 0.745, "a) 离线确定性复核", size=11, weight="bold", color=BROWN, ha="left", va="center")
    _rf_role(ax, 0.095, 0.600, 0.105, 0.100, "offline", accent="#7dd3fc", tool="trace")
    offline = [("pytest\n参数化断言", "trace"), ("mock LLM\n纯内存", "brain"), ("红队\n358场景", "risk"), ("11类\n工具链回放", "tool")]
    for i, (label, icon) in enumerate(offline):
        x = 0.230 + (i % 2) * 0.115
        y = 0.600 - (i // 2) * 0.160
        _rf_node(ax, x, y, 0.092, 0.090, label, icon, fs=5.9)
    _rf_panel(ax, 0.105, 0.300, 0.300, 0.055, fc="#fffdf8", ec="#cbd5e1", lw=0.8, dashed=False, radius=0.008)
    _rf_text(ax, 0.255, 0.328, "形成主要可复现实验证据", size=7.2, weight="bold", ha="center", va="center")

    _rf_panel(ax, 0.540, 0.220, 0.395, 0.565, fc=LANE_GREEN, ec="#8a8a8a", lw=1.1, dashed=True)
    _rf_text(ax, 0.565, 0.745, "b) 本机工具流联调", size=11, weight="bold", color=BROWN, ha="left", va="center")
    _rf_role(ax, 0.565, 0.600, 0.105, 0.100, "local", accent="#a7f3d0", tool="laptop")
    local = [("Telegram\nDM入口", "message"), ("OpenClaw\nGateway", "tool"), ("runtime\ncontract", "shield"), ("SQLite\nTrace证据", "db")]
    for i, (label, icon) in enumerate(local):
        x = 0.700 + (i % 2) * 0.115
        y = 0.600 - (i // 2) * 0.160
        _rf_node(ax, x, y, 0.092, 0.090, label, icon, fs=5.9)
    _rf_panel(ax, 0.585, 0.300, 0.300, 0.055, fc="#fffdf8", ec="#cbd5e1", lw=0.8, dashed=False, radius=0.008)
    _rf_text(ax, 0.735, 0.328, "验证真实入口与 provider 链路", size=7.2, weight="bold", ha="center", va="center")

    _rf_arrow(ax, (0.265, 0.220), (0.465, 0.160), color=GOLD, lw=3.0, rad=0.12)
    _rf_arrow(ax, (0.735, 0.220), (0.535, 0.160), color=GOLD, lw=3.0, rad=-0.12)
    _rf_panel(ax, 0.360, 0.105, 0.280, 0.070, fc="#fffdf8", ec=PAPER_EDGE, lw=1.0, dashed=False, radius=0.010)
    _rf_text(ax, 0.500, 0.140, "证据互补；不混用外部 benchmark 数值", size=7.6, weight="bold", color=BROWN, ha="center", va="center")
    _save_fallback(fig, output_dir)


RENDERERS = {
    "fig_trust_boundaries": _render_trust_boundaries_researcher,
    "fig_architecture": _render_architecture_researcher,
    "fig_proxy_pipeline": _render_proxy_pipeline_researcher,
    "fig_agent_pipeline": _render_agent_pipeline_researcher,
    "fig_intervention_flow": _render_intervention_flow_researcher,
    "fig_tool_gate_state_machine": _render_tool_gate_state_machine_researcher,
    "fig_delegation": _render_delegation_researcher,
    "fig_trace_evidence": _render_trace_evidence_researcher,
    "fig_evidence_scope": _render_evidence_scope_researcher,
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
        "renderer": "researcher_style_matplotlib",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reason": "Deterministic local renderer used; external AutoFigure-Edit is optional.",
        "style": "Researcher/CycleResearcher-inspired academic process art: warm paper, dashed frames, pastel panels, thick arrows, original vector icons",
        "pdf": str(pdf_path.relative_to(ROOT)),
    }
    (output_dir / "evaluation.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "generation_log.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_contact_sheet() -> None:
    try:
        from PIL import Image, ImageDraw
    except Exception as exc:  # pragma: no cover - optional preview helper
        print(f"Skipping contact sheet because Pillow is unavailable: {exc}")
        return

    images: list[tuple[str, Image.Image]] = []
    for spec in FIGURES:
        path = OUTPUT_DIR / spec.slug / "figure.png"
        if not path.exists():
            continue
        img = Image.open(path).convert("RGB")
        img.thumbnail((520, 260), Image.LANCZOS)
        images.append((spec.slug, img))
    if not images:
        return

    cols = 3
    pad = 24
    title_h = 28
    cell_w = 560
    cell_h = 320
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w + pad, rows * cell_h + pad), "#fffaf0")
    draw = ImageDraw.Draw(sheet)
    for idx, (slug, img) in enumerate(images):
        col = idx % cols
        row = idx // cols
        x = pad + col * cell_w
        y = pad + row * cell_h
        draw.text((x, y), slug, fill="#172033")
        sheet.paste(img, (x, y + title_h))
    CONTACT_SHEET.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(CONTACT_SHEET)


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
        "--optimize_iterations",
        str(args.optimize_iterations),
    ]
    if args.base_url:
        cmd.extend(["--base_url", args.base_url])
    if args.image_provider:
        cmd.extend(["--image_provider", args.image_provider])
    if args.image_api_key:
        cmd.extend(["--image_api_key", args.image_api_key])
    if args.image_base_url:
        cmd.extend(["--image_base_url", args.image_base_url])
    if args.svg_model:
        cmd.extend(["--svg_model", args.svg_model])
    if args.image_model:
        cmd.extend(["--image_model", args.image_model])
    if args.image_size:
        cmd.extend(["--image_size", args.image_size])
    if args.sam_backend:
        cmd.extend(["--sam_backend", args.sam_backend])
    if args.reference_image_path:
        if args.use_reference_image:
            cmd.append("--use_reference_image")
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
    parser.add_argument("--style-preset", choices=["researcher"], default=os.environ.get("AUTOFIGURE_STYLE_PRESET", "researcher"))
    parser.add_argument("--autofigure-dir", default=_default_autofigure_dir())
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", ""))
    parser.add_argument("--provider", default=os.environ.get("AUTOFIGURE_PROVIDER", "openai_response"))
    parser.add_argument("--base-url", default=os.environ.get("AUTOFIGURE_BASE_URL", os.environ.get("OPENAI_BASE_URL", "")))
    parser.add_argument("--image-provider", default=os.environ.get("AUTOFIGURE_IMAGE_PROVIDER", ""))
    parser.add_argument("--image-api-key", default=os.environ.get("AUTOFIGURE_IMAGE_API_KEY", ""))
    parser.add_argument("--image-base-url", default=os.environ.get("AUTOFIGURE_IMAGE_BASE_URL", ""))
    parser.add_argument("--svg-model", default=os.environ.get("AUTOFIGURE_SVG_MODEL", "gpt-5.5"))
    parser.add_argument("--image-model", default=os.environ.get("AUTOFIGURE_IMAGE_MODEL", "gpt-image-2"))
    parser.add_argument("--image-size", default=os.environ.get("AUTOFIGURE_IMAGE_SIZE", ""))
    parser.add_argument("--optimize-iterations", type=int, default=int(os.environ.get("AUTOFIGURE_OPTIMIZE_ITERATIONS", "0")))
    parser.add_argument("--sam-backend", default=os.environ.get("AUTOFIGURE_SAM_BACKEND", ""))
    parser.add_argument("--reference-image-path", default=os.environ.get("AUTOFIGURE_REFERENCE_IMAGE_PATH", ""))
    parser.add_argument("--use-reference-image", action="store_true", default=os.environ.get("AUTOFIGURE_USE_REFERENCE_IMAGE", "").lower() in {"1", "true", "yes"})
    parser.add_argument("--preview-contact-sheet", action="store_true", help="Write a PNG contact sheet of all generated structural figures.")
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
        if args.preview_contact_sheet:
            _make_contact_sheet()
        return 0

    for spec in FIGURES:
        output_dir = OUTPUT_DIR / spec.slug
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        _run_autofigure(spec, args, output_dir)
    if args.preview_contact_sheet:
        _make_contact_sheet()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
