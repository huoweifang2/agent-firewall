#!/usr/bin/env node
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const ARTICLE_DIR = path.dirname(__filename);
const IMAGE_DIR = path.join(ARTICLE_DIR, "images");
const LATEX_FIGURE_DIR = path.join(ARTICLE_DIR, "latex", "figures");
const SOURCE_DIR = path.join(IMAGE_DIR, "excalidraw_sources");
const SVG_DIR = path.join(IMAGE_DIR, "excalidraw_svg");
const HTML_DIR = path.join(IMAGE_DIR, ".excalidraw_render_html");
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const W = 1800;
const H = 1040;
const FONT = "Songti SC, PingFang SC, Heiti SC, Arial Unicode MS, sans-serif";
const COLORS = {
  ink: "#172033",
  muted: "#64748b",
  line: "#334155",
  ingress: ["#fee2e2", "#dc2626"],
  proxy: ["#dcfce7", "#16a34a"],
  runtime: ["#dbeafe", "#2563eb"],
  llm: ["#fef3c7", "#ca8a04"],
  gate: ["#ffedd5", "#f97316"],
  provider: ["#ede9fe", "#7c3aed"],
  audit: ["#f1f5f9", "#475569"],
  allow: ["#dcfce7", "#16a34a"],
  block: ["#fee2e2", "#dc2626"],
  modify: ["#fef3c7", "#ca8a04"],
  note: ["#ccfbf1", "#0891b2"],
  laneBlue: "#eff6ff",
  laneGreen: "#f0fdf4",
  laneYellow: "#fffbeb",
  lanePurple: "#faf5ff",
  laneRed: "#fff1f2",
  laneGray: "#f8fafc",
};

const SOURCE_NOTES = {
  "fig_2_1_trust_boundaries": "article/images/mermaid_sources/fig_2_1_trust_boundaries.mmd",
  "fig_3_1_architecture": "article/images/mermaid_sources/fig_3_1_architecture.mmd",
  "fig_4_1_method_overview": "article/images/mermaid_sources/fig_4_1_method_overview.mmd",
  "fig_4_2_scan_pipeline": "article/images/mermaid_sources/fig_4_2_scan_pipeline.mmd",
  "fig_4_3_risk_decision": "article/images/mermaid_sources/fig_4_3_risk_decision.mmd",
  "fig_4_4_agent_runtime_graph": "article/images/mermaid_sources/fig_4_4_agent_runtime_graph.mmd",
  "fig_4_5_pre_tool_gate": "article/images/mermaid_sources/fig_4_5_pre_tool_gate.mmd",
  "fig_4_6_post_tool_gate": "article/images/mermaid_sources/fig_4_6_post_tool_gate.mmd",
  "fig_4_7_openclaw_bridge": "article/images/mermaid_sources/fig_4_7_openclaw_bridge.mmd",
  "fig_4_8_intervention_state": "article/images/mermaid_sources/fig_4_8_intervention_state.mmd",
  "fig_4_9_trace_evidence": "article/images/mermaid_sources/fig_4_9_trace_evidence.mmd",
};

function ensureDirs() {
  [SOURCE_DIR, SVG_DIR, HTML_DIR, LATEX_FIGURE_DIR].forEach((dir) => fs.mkdirSync(dir, { recursive: true }));
}

function esc(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function wrapLine(line, maxChars) {
  const out = [];
  let current = "";
  for (const char of String(line)) {
    const width = /[\u4e00-\u9fff]/.test(char) ? 1 : 0.58;
    const curWidth = [...current].reduce((sum, ch) => sum + (/[\u4e00-\u9fff]/.test(ch) ? 1 : 0.58), 0);
    if (curWidth + width > maxChars && current) {
      out.push(current.trim());
      current = char;
    } else {
      current += char;
    }
  }
  if (current.trim()) out.push(current.trim());
  return out;
}

function wrapText(text, maxChars = 14) {
  return String(text)
    .split("\n")
    .flatMap((line) => wrapLine(line, maxChars));
}

function textSvg(text, x, y, options = {}) {
  const {
    size = 30,
    weight = 500,
    color = COLORS.ink,
    anchor = "middle",
    lineHeight = 1.22,
    maxChars = 14,
  } = options;
  const lines = wrapText(text, maxChars);
  const total = (lines.length - 1) * size * lineHeight;
  const firstY = y - total / 2;
  return `<text x="${x}" y="${firstY}" text-anchor="${anchor}" dominant-baseline="middle" fill="${color}" font-family="${FONT}" font-size="${size}" font-weight="${weight}">${lines
    .map((line, index) => `<tspan x="${x}" dy="${index === 0 ? 0 : size * lineHeight}">${esc(line)}</tspan>`)
    .join("")}</text>`;
}

function c(type) {
  return COLORS[type] || COLORS.audit;
}

function node(id, label, x, y, w, h, type = "runtime", icon = "node", extra = {}) {
  const [fill, stroke] = c(type);
  return { id, label, x, y, w, h, type, icon, fill, stroke, ...extra };
}

function lane(label, x, y, w, h, fill = COLORS.laneGray) {
  return { label, x, y, w, h, fill };
}

function center(n) {
  return [n.x + n.w / 2, n.y + n.h / 2];
}

function sidePoint(n, side) {
  if (side === "left") return [n.x, n.y + n.h / 2];
  if (side === "right") return [n.x + n.w, n.y + n.h / 2];
  if (side === "top") return [n.x + n.w / 2, n.y];
  if (side === "bottom") return [n.x + n.w / 2, n.y + n.h];
  return center(n);
}

function anchor(from, to, fromSide = null, toSide = null) {
  if (fromSide || toSide) {
    const [sx, sy] = sidePoint(from, fromSide || "right");
    const [ex, ey] = sidePoint(to, toSide || "left");
    return [sx, sy, ex, ey];
  }
  const [fx, fy] = center(from);
  const [tx, ty] = center(to);
  const dx = tx - fx;
  const dy = ty - fy;
  if (Math.abs(dx) >= Math.abs(dy)) {
    return dx >= 0
      ? [from.x + from.w, fy, to.x, ty]
      : [from.x, fy, to.x + to.w, ty];
  }
  return dy >= 0
    ? [fx, from.y + from.h, tx, to.y]
    : [fx, from.y, tx, to.y + to.h];
}

function orthogonalPoints(start, end, via = []) {
  const points = [start];
  let [cx, cy] = start;
  for (const bend of via) {
    const [vx, vy] = bend;
    if (vx !== cx && vy !== cy) {
      points.push([vx, cy]);
    }
    points.push([vx, vy]);
    cx = vx;
    cy = vy;
  }
  const [ex, ey] = end;
  if (ex !== cx && ey !== cy) {
    if (Math.abs(ex - cx) > Math.abs(ey - cy)) {
      points.push([ex, cy]);
    } else {
      points.push([cx, ey]);
    }
  }
  points.push(end);
  return points;
}

function defaultRoute(start, end) {
  const [sx, sy] = start;
  const [ex, ey] = end;
  if (Math.abs(ex - sx) > Math.abs(ey - sy)) {
    const mid = sx + (ex - sx) / 2;
    return [[sx, sy], [mid, sy], [mid, ey], [ex, ey]];
  }
  const mid = sy + (ey - sy) / 2;
  return [[sx, sy], [sx, mid], [ex, mid], [ex, ey]];
}

function iconSvg(icon, x, y, color) {
  const s = 36;
  const cx = x + 34;
  const cy = y + 34;
  const common = `stroke="${color}" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"`;
  if (icon === "shield") {
    return `<path ${common} d="M${cx} ${cy - 17} L${cx + 16} ${cy - 10} C${cx + 13} ${cy + 10} ${cx + 5} ${cy + 18} ${cx} ${cy + 22} C${cx - 5} ${cy + 18} ${cx - 13} ${cy + 10} ${cx - 16} ${cy - 10} Z"/><path ${common} d="M${cx - 8} ${cy + 1} L${cx - 2} ${cy + 8} L${cx + 10} ${cy - 7}"/>`;
  }
  if (icon === "db") {
    return `<ellipse ${common} cx="${cx}" cy="${cy - 11}" rx="${s / 2}" ry="8"/><path ${common} d="M${cx - s / 2} ${cy - 11} v26 c0 5 8 8 18 8 s18 -3 18 -8 v-26"/><path ${common} d="M${cx - s / 2} ${cy + 2} c0 5 8 8 18 8 s18 -3 18 -8"/>`;
  }
  if (icon === "chip") {
    return `<rect ${common} x="${cx - 15}" y="${cy - 15}" width="30" height="30" rx="5"/><path ${common} d="M${cx - 7} ${cy - 23} v8 M${cx + 7} ${cy - 23} v8 M${cx - 7} ${cy + 15} v8 M${cx + 7} ${cy + 15} v8 M${cx - 23} ${cy - 7} h8 M${cx - 23} ${cy + 7} h8 M${cx + 15} ${cy - 7} h8 M${cx + 15} ${cy + 7} h8"/>`;
  }
  if (icon === "tool") {
    return `<path ${common} d="M${cx - 14} ${cy + 15} L${cx + 5} ${cy - 4}"/><path ${common} d="M${cx + 7} ${cy - 17} c6 3 8 10 4 16 l-10 -10 7 -6z"/><circle ${common} cx="${cx - 15}" cy="${cy + 16}" r="4"/>`;
  }
  if (icon === "doc") {
    return `<path ${common} d="M${cx - 13} ${cy - 18} h19 l10 10 v26 h-29 z"/><path ${common} d="M${cx + 6} ${cy - 18} v10 h10 M${cx - 5} ${cy - 2} h15 M${cx - 5} ${cy + 8} h15"/>`;
  }
  if (icon === "user") {
    return `<circle ${common} cx="${cx}" cy="${cy - 9}" r="9"/><path ${common} d="M${cx - 18} ${cy + 20} c4 -13 32 -13 36 0"/>`;
  }
  if (icon === "terminal") {
    return `<rect ${common} x="${cx - 22}" y="${cy - 17}" width="44" height="34" rx="5"/><path ${common} d="M${cx - 14} ${cy - 6} l8 6 -8 6 M${cx + 2} ${cy + 7} h12"/>`;
  }
  if (icon === "stop") {
    return `<path ${common} d="M${cx - 11} ${cy - 20} h22 l15 15 v22 l-15 15 h-22 l-15 -15 v-22 z"/><path ${common} d="M${cx - 10} ${cy - 10} l20 20 M${cx + 10} ${cy - 10} l-20 20"/>`;
  }
  if (icon === "ok") {
    return `<circle ${common} cx="${cx}" cy="${cy}" r="22"/><path ${common} d="M${cx - 11} ${cy + 1} l8 8 l16 -20"/>`;
  }
  if (icon === "edit") {
    return `<path ${common} d="M${cx - 17} ${cy + 14} l5 -17 l20 -20 l12 12 l-20 20 z"/><path ${common} d="M${cx - 8} ${cy - 13} l12 12"/>`;
  }
  if (icon === "msg") {
    return `<path ${common} d="M${cx - 22} ${cy - 16} h44 v27 h-28 l-12 10 v-10 h-4 z"/><path ${common} d="M${cx - 12} ${cy - 5} h24 M${cx - 12} ${cy + 5} h16"/>`;
  }
  return `<circle ${common} cx="${cx}" cy="${cy}" r="20"/><path ${common} d="M${cx - 10} ${cy} h20 M${cx} ${cy - 10} v20"/>`;
}

function nodeSvg(n) {
  const shape =
    n.shape === "diamond"
      ? `<path d="M${n.x + n.w / 2} ${n.y} L${n.x + n.w} ${n.y + n.h / 2} L${n.x + n.w / 2} ${n.y + n.h} L${n.x} ${n.y + n.h / 2} Z" fill="${n.fill}" stroke="${n.stroke}" stroke-width="3"/>`
      : `<rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="18" fill="${n.fill}" stroke="${n.stroke}" stroke-width="3"/>`;
  const textX = n.shape === "diamond" ? n.x + n.w / 2 : n.x + n.w / 2 + 24;
  const maxChars = n.maxChars || Math.max(8, Math.floor((n.w - 86) / 24));
  const icon = n.shape === "diamond" ? "" : iconSvg(n.icon, n.x + 12, n.y + 14, n.stroke);
  return `<g filter="url(#softShadow)">${shape}${icon}${textSvg(n.label, textX, n.y + n.h / 2, {
    size: n.fontSize || 27,
    weight: n.weight || 650,
    maxChars,
  })}</g>`;
}

function arrowSvg(edge, nodeMap) {
  const from = nodeMap.get(edge.from);
  const to = nodeMap.get(edge.to);
  let points = [];
  if (from && to) {
    const [sx, sy, ex, ey] = anchor(from, to, edge.fromSide, edge.toSide);
    if (edge.route === "straight") {
      points = [[sx, sy], [ex, ey]];
    } else if (edge.via) {
      points = orthogonalPoints([sx, sy], [ex, ey], edge.via);
    } else {
      points = defaultRoute([sx, sy], [ex, ey]);
    }
  } else if (edge.points) {
    points = edge.points;
  } else {
    return "";
  }
  const d = points.map((p, index) => `${index === 0 ? "M" : "L"}${p[0]} ${p[1]}`).join(" ");
  const stroke = edge.color || COLORS.line;
  const dash = edge.dashed ? `stroke-dasharray="12 10"` : "";
  const label = edge.label
    ? textSvg(edge.label, (points[0][0] + points.at(-1)[0]) / 2 + (edge.labelDx || 0), (points[0][1] + points.at(-1)[1]) / 2 + (edge.labelDy || 0), {
        size: 22,
        weight: 650,
        color: stroke,
        maxChars: 10,
      })
    : "";
  return `<g><path d="${d}" fill="none" stroke="${stroke}" stroke-width="${edge.width || 5}" ${dash} marker-end="url(#arrowhead)" stroke-linecap="round" stroke-linejoin="round"/>${label}</g>`;
}

function renderSvg(spec) {
  const nodes = spec.nodes || [];
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const lanes = (spec.lanes || [])
    .map(
      (l) =>
        `<g><rect x="${l.x}" y="${l.y}" width="${l.w}" height="${l.h}" rx="26" fill="${l.fill}" stroke="#94a3b8" stroke-width="2.5" stroke-dasharray="14 10"/><text x="${l.x + 24}" y="${l.y + 38}" fill="${COLORS.ink}" font-family="${FONT}" font-size="26" font-weight="700">${esc(l.label)}</text></g>`,
    )
    .join("\n");
  const notes = (spec.notes || [])
    .map((n) => {
      const [fill, stroke] = c(n.type || "note");
      return `<g><rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="18" fill="${fill}" stroke="${stroke}" stroke-width="2.5" stroke-dasharray="${n.dashed ? "10 8" : "0"}"/>${textSvg(n.label, n.x + n.w / 2, n.y + n.h / 2, { size: n.size || 24, weight: 650, maxChars: n.maxChars || 18 })}</g>`;
    })
    .join("\n");
  const edges = (spec.edges || []).map((edge) => arrowSvg(edge, nodeMap)).join("\n");
  const nodeShapes = nodes.map(nodeSvg).join("\n");
  const footer = spec.footer
    ? `<text x="${W / 2}" y="${H - 36}" text-anchor="middle" fill="${COLORS.muted}" font-family="${FONT}" font-size="22">${esc(spec.footer)}</text>`
    : "";
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <defs>
    <filter id="softShadow" x="-10%" y="-10%" width="120%" height="130%">
      <feDropShadow dx="0" dy="6" stdDeviation="5" flood-color="#0f172a" flood-opacity="0.12"/>
    </filter>
    <marker id="arrowhead" markerWidth="18" markerHeight="18" refX="16" refY="6" orient="auto" markerUnits="userSpaceOnUse">
      <path d="M0,0 L16,6 L0,12 z" fill="${COLORS.line}"/>
    </marker>
  </defs>
  <rect width="${W}" height="${H}" fill="#ffffff"/>
  <text x="72" y="68" fill="${COLORS.ink}" font-family="${FONT}" font-size="38" font-weight="800">${esc(spec.title)}</text>
  ${spec.subtitle ? `<text x="72" y="108" fill="${COLORS.muted}" font-family="${FONT}" font-size="22">${esc(spec.subtitle)}</text>` : ""}
  ${lanes}
  ${edges}
  ${nodeShapes}
  ${notes}
  ${footer}
</svg>`;
}

function excalidrawBase(element) {
  return {
    id: element.id,
    x: element.x,
    y: element.y,
    width: element.w,
    height: element.h,
    angle: 0,
    strokeColor: element.stroke || COLORS.line,
    backgroundColor: element.fill || "transparent",
    fillStyle: "solid",
    strokeWidth: 2,
    strokeStyle: "solid",
    roughness: 1,
    opacity: 100,
    groupIds: [],
    frameId: null,
    roundness: { type: 3 },
    seed: element.seed || 1000,
    version: 1,
    versionNonce: element.seed || 1000,
    isDeleted: false,
    boundElements: null,
    updated: 1,
    link: null,
    locked: false,
  };
}

function excalidrawElements(spec, slug) {
  let index = 1;
  const elements = [];
  const add = (element) => {
    elements.push(element);
    return element;
  };
  add({
    ...excalidrawBase({
      id: `${slug}_title`,
      x: 72,
      y: 36,
      w: 920,
      h: 48,
      stroke: "transparent",
      fill: "transparent",
      seed: index++,
    }),
    type: "text",
    text: spec.title,
    originalText: spec.title,
    fontSize: 34,
    fontFamily: 2,
    textAlign: "left",
    verticalAlign: "top",
    baseline: 38,
    containerId: null,
    lineHeight: 1.25,
  });
  for (const l of spec.lanes || []) {
    add({
      ...excalidrawBase({
        id: `${slug}_lane_${index}`,
        x: l.x,
        y: l.y,
        w: l.w,
        h: l.h,
        stroke: "#94a3b8",
        fill: l.fill,
        seed: index++,
      }),
      type: "rectangle",
      strokeStyle: "dashed",
    });
    add({
      ...excalidrawBase({
        id: `${slug}_lane_text_${index}`,
        x: l.x + 22,
        y: l.y + 16,
        w: 360,
        h: 34,
        stroke: "transparent",
        fill: "transparent",
        seed: index++,
      }),
      type: "text",
      text: l.label,
      originalText: l.label,
      fontSize: 25,
      fontFamily: 2,
      textAlign: "left",
      verticalAlign: "top",
      baseline: 28,
      containerId: null,
      lineHeight: 1.25,
    });
  }
  const nodeMap = new Map((spec.nodes || []).map((n) => [n.id, n]));
  for (const e of spec.edges || []) {
    const from = nodeMap.get(e.from);
    const to = nodeMap.get(e.to);
    let route = null;
    if (from && to) {
      const [sx, sy, ex, ey] = anchor(from, to, e.fromSide, e.toSide);
      route = e.route === "straight"
        ? [[sx, sy], [ex, ey]]
        : e.via
          ? orthogonalPoints([sx, sy], [ex, ey], e.via)
          : defaultRoute([sx, sy], [ex, ey]);
    } else if (e.points) {
      route = e.points;
    }
    if (!route) continue;
    const xs = route.map((p) => p[0]);
    const ys = route.map((p) => p[1]);
    const x = Math.min(...xs);
    const y = Math.min(...ys);
    const w = Math.max(...xs) - x;
    const h = Math.max(...ys) - y;
    add({
      ...excalidrawBase({
        id: `${slug}_edge_${index}`,
        x,
        y,
        w,
        h,
        stroke: e.color || COLORS.line,
        fill: "transparent",
        seed: index++,
      }),
      type: "arrow",
      points: route.map((p) => [p[0] - x, p[1] - y]),
      lastCommittedPoint: null,
      startBinding: null,
      endBinding: null,
      startArrowhead: null,
      endArrowhead: "arrow",
      strokeStyle: e.dashed ? "dashed" : "solid",
    });
  }
  for (const n of spec.nodes || []) {
    add({
      ...excalidrawBase({
        id: `${slug}_${n.id}`,
        x: n.x,
        y: n.y,
        w: n.w,
        h: n.h,
        stroke: n.stroke,
        fill: n.fill,
        seed: index++,
      }),
      type: n.shape === "diamond" ? "diamond" : "rectangle",
    });
    if (n.shape !== "diamond") {
      add({
        ...excalidrawBase({
          id: `${slug}_${n.id}_icon`,
          x: n.x + 22,
          y: n.y + n.h / 2 - 20,
          w: 40,
          h: 40,
          stroke: n.stroke,
          fill: "transparent",
          seed: index++,
        }),
        type: "ellipse",
      });
    }
    add({
      ...excalidrawBase({
        id: `${slug}_${n.id}_text`,
        x: n.x + (n.shape === "diamond" ? 20 : 78),
        y: n.y + 22,
        w: n.w - (n.shape === "diamond" ? 40 : 92),
        h: n.h - 32,
        stroke: "transparent",
        fill: "transparent",
        seed: index++,
      }),
      type: "text",
      text: n.label,
      originalText: n.label,
      fontSize: n.fontSize || 24,
      fontFamily: 2,
      textAlign: n.shape === "diamond" ? "center" : "center",
      verticalAlign: "middle",
      baseline: n.h - 34,
      containerId: null,
      lineHeight: 1.2,
    });
  }
  for (const n of spec.notes || []) {
    const [fill, stroke] = c(n.type || "note");
    add({
      ...excalidrawBase({
        id: `${slug}_note_${index}`,
        x: n.x,
        y: n.y,
        w: n.w,
        h: n.h,
        stroke,
        fill,
        seed: index++,
      }),
      type: "rectangle",
      strokeStyle: n.dashed ? "dashed" : "solid",
    });
    add({
      ...excalidrawBase({
        id: `${slug}_note_text_${index}`,
        x: n.x + 18,
        y: n.y + 16,
        w: n.w - 36,
        h: n.h - 24,
        stroke: "transparent",
        fill: "transparent",
        seed: index++,
      }),
      type: "text",
      text: n.label,
      originalText: n.label,
      fontSize: n.size || 23,
      fontFamily: 2,
      textAlign: "center",
      verticalAlign: "middle",
      baseline: n.h - 26,
      containerId: null,
      lineHeight: 1.2,
    });
  }
  return elements;
}

function writeExcalidraw(spec, slug) {
  const file = {
    type: "excalidraw",
    version: 2,
    source: "https://excalidraw.com",
    elements: excalidrawElements(spec, slug),
    appState: {
      viewBackgroundColor: "#ffffff",
      currentItemFontFamily: 2,
      gridSize: null,
    },
    files: {},
  };
  const note = SOURCE_NOTES[slug] || spec.source || "";
  const payload = {
    ...file,
    appState: {
      ...file.appState,
      name: slug,
      exportBackground: true,
      exportScale: 2,
    },
    metadata: {
      generator: "article/generate_excalidraw_flowcharts.mjs",
      source: note,
      style: "Excalidraw hand-drawn technical diagram, native vector elements, no external bitmap icons",
    },
  };
  fs.writeFileSync(path.join(SOURCE_DIR, `${slug}.excalidraw`), JSON.stringify(payload, null, 2), "utf8");
}

function renderWithChrome(svgPath, htmlPath, pngPath, pdfPath) {
  const html = `<!doctype html><html><head><meta charset="utf-8"><style>
@page { size: ${W}px ${H}px; margin: 0; }
html, body { margin: 0; width: ${W}px; height: ${H}px; overflow: hidden; background: white; }
img { display: block; width: ${W}px; height: ${H}px; }
</style></head><body><img src="${pathToFileURL(svgPath).href}"></body></html>`;
  fs.writeFileSync(htmlPath, html, "utf8");
  const url = pathToFileURL(htmlPath).href;
  execFileSync(CHROME, [
    "--headless=new",
    "--disable-gpu",
    "--allow-file-access-from-files",
    "--hide-scrollbars",
    "--force-device-scale-factor=2",
    `--window-size=${W},${H}`,
    `--screenshot=${pngPath}`,
    url,
  ], { stdio: "ignore" });
  if (pdfPath) {
    execFileSync(CHROME, [
      "--headless=new",
      "--disable-gpu",
      "--allow-file-access-from-files",
      "--no-pdf-header-footer",
      `--window-size=${W},${H}`,
      `--print-to-pdf=${pdfPath}`,
      url,
    ], { stdio: "ignore" });
  }
}

function cardRow(ids, labels, x, y, w, h, gap, type, icons = []) {
  return labels.map((label, index) => node(ids[index], label, x + index * (w + gap), y, w, h, type[index] || type, icons[index] || "node"));
}

function figureSpecs() {
  const specs = {};
  specs.trust = {
    title: "系统资产流转与主要信任边界",
    subtitle: "跨边界数据先检查、再进入下一阶段",
    lanes: [
      lane("外部输入边界", 70, 150, 1660, 210, COLORS.laneRed),
      lane("受保护运行链路", 70, 390, 1660, 250, COLORS.laneGreen),
      lane("审计与复核", 70, 675, 1660, 190, COLORS.laneGray),
    ],
    nodes: [
      node("msg", "外部消息入口\nTelegram / 后续入口", 130, 220, 250, 118, "ingress", "msg"),
      node("scan", "模型前控制点\n/agent/chat + /v1/scan", 450, 220, 285, 118, "proxy", "shield"),
      node("plan", "工具计划控制点\nLLM plan + pre-tool gate", 805, 220, 300, 118, "gate", "chip"),
      node("tool", "工具输出控制点\nOpenClaw skill + post-tool gate", 1175, 220, 330, 118, "provider", "tool"),
      node("trace", "Trace / Audit\n证据落盘", 660, 720, 300, 110, "audit", "doc"),
      node("b1", "边界 1\n入口不可信", 410, 440, 260, 98, "block", "stop"),
      node("b2", "边界 2\n工具计划不可信", 760, 440, 280, 98, "block", "stop"),
      node("b3", "边界 3\n工具结果不可信", 1130, 440, 280, 98, "block", "stop"),
    ],
    edges: [
      { from: "msg", to: "scan" },
      { from: "scan", to: "plan" },
      { from: "plan", to: "tool" },
      { from: "tool", to: "trace", dashed: true, label: "记录" },
      { from: "b1", to: "scan", dashed: true, color: COLORS.block[1] },
      { from: "b2", to: "plan", dashed: true, color: COLORS.block[1] },
      { from: "b3", to: "tool", dashed: true, color: COLORS.block[1] },
    ],
    notes: [
      { x: 1020, y: 720, w: 515, h: 110, label: "控制原则：用户输入、模型工具计划和工具结果均不能直接跨越安全边界。", type: "note", maxChars: 24 },
    ],
  };

  specs.architecture = {
    title: "Agent-Firewall 总体架构",
    subtitle: "入口、安全壳、工具生态与本地控制台解耦",
    lanes: [
      lane("入口适配", 70, 145, 330, 760, COLORS.laneRed),
      lane("Agent Runtime :8002", 440, 145, 430, 760, COLORS.laneBlue),
      lane("Proxy Service :8000", 910, 145, 380, 760, COLORS.laneGreen),
      lane("工具生态 / 证据", 1330, 145, 400, 760, COLORS.lanePurple),
    ],
    nodes: [
      node("telegram", "Telegram Bridge\n外部消息适配", 115, 235, 245, 110, "ingress", "msg"),
      node("other", "其他入口\n统一调用 /agent/chat", 115, 420, 245, 110, "ingress", "terminal"),
      node("console", "Nuxt / Vuetify\n本地控制台", 115, 650, 245, 125, "runtime", "terminal"),
      node("runtime", "运行图\n会话 / 角色 / 策略", 490, 220, 300, 115, "runtime", "chip"),
      node("llm", "LLM 调用\nDeepSeek", 490, 420, 300, 110, "llm", "chip"),
      node("gates", "pre / post gate\n工具前后门控", 490, 640, 300, 115, "gate", "shield"),
      node("scan", "/v1/scan\nscan-only 输入扫描", 955, 220, 285, 115, "proxy", "shield"),
      node("control", "Control Plane\nruntime spec", 955, 420, 285, 110, "proxy", "doc"),
      node("inter", "/v1/interventions\n审批队列", 955, 640, 285, 115, "proxy", "user"),
      node("openclaw", "OpenClaw skills / hooks", 1385, 270, 295, 115, "provider", "tool"),
      node("mcp", "MCP provider slot\n扩展边界", 1385, 465, 295, 115, "provider", "terminal"),
      node("store", "SQLite + Memory\nTrace / Audit / Intervention", 1385, 680, 295, 120, "audit", "db"),
    ],
    edges: [
      { from: "telegram", to: "runtime", fromSide: "right", toSide: "left" },
      { from: "other", to: "runtime", fromSide: "right", toSide: "left", via: [[410, 475]] },
      { from: "runtime", to: "llm", fromSide: "bottom", toSide: "top" },
      { from: "llm", to: "gates", fromSide: "bottom", toSide: "top" },
      { from: "runtime", to: "scan", fromSide: "right", toSide: "left", label: "输入预扫" },
      { from: "control", to: "runtime", dashed: true, fromSide: "left", toSide: "right", label: "runtime spec" },
      { from: "inter", to: "gates", dashed: true, fromSide: "left", toSide: "right", label: "审批状态" },
      { from: "gates", to: "openclaw", fromSide: "right", toSide: "left" },
      { from: "gates", to: "mcp", dashed: true, fromSide: "right", toSide: "left", via: [[1265, 700], [1265, 522]] },
      { from: "console", to: "control", dashed: true, fromSide: "right", toSide: "left", via: [[410, 712], [410, 475]] },
      { from: "scan", to: "store", dashed: true, fromSide: "right", toSide: "left", via: [[1310, 278], [1310, 740]] },
    ],
  };

  specs.method = {
    title: "方法总览与工具调用安全状态流",
    subtitle: "模型调用前、工具执行前、工具执行后三道控制点",
    lanes: [
      lane("模型调用前", 70, 150, 520, 530, COLORS.laneGreen),
      lane("工具执行前", 640, 150, 500, 530, COLORS.laneYellow),
      lane("工具执行后", 1190, 150, 540, 530, COLORS.lanePurple),
    ],
    nodes: [
      node("user", "用户消息", 130, 245, 210, 100, "ingress", "msg"),
      node("parse", "输入解析\n会话加载", 130, 430, 210, 100, "runtime", "doc"),
      node("scan", "Proxy /v1/scan\n风险判断", 130, 585, 260, 100, "proxy", "shield"),
      node("llm", "LLM 回复\n或工具计划", 710, 245, 260, 100, "llm", "chip"),
      node("pre", "pre-tool gate\nRBAC / Schema / 限额", 710, 430, 310, 105, "gate", "shield"),
      node("provider", "Provider\nOpenClaw / MCP slot", 1260, 245, 300, 100, "provider", "tool"),
      node("post", "post-tool gate\nPII / Secrets / 注入", 1260, 430, 310, 105, "gate", "shield"),
      node("reply", "最终回复", 1305, 610, 230, 95, "audit", "doc"),
      node("inputBlock", "input_block\n模型前阻断", 405, 585, 250, 100, "block", "stop"),
      node("toolBlock", "tool_block / confirmation\n真实工具前暂停", 835, 610, 330, 100, "block", "stop"),
      node("output", "output_block / redact / truncate\n进入上下文前处理", 1185, 775, 390, 100, "modify", "edit"),
      node("trace", "Trace / Audit\n输入、计划、门控、执行、清洗", 650, 805, 390, 100, "note", "doc"),
    ],
    edges: [
      { from: "user", to: "parse", fromSide: "bottom", toSide: "top" },
      { from: "parse", to: "scan", fromSide: "bottom", toSide: "top" },
      { from: "scan", to: "llm", fromSide: "right", toSide: "left", label: "ALLOW / MODIFY", via: [[600, 635], [600, 295]] },
      { from: "scan", to: "inputBlock", fromSide: "right", toSide: "left", color: COLORS.block[1], label: "BLOCK" },
      { from: "llm", to: "pre", fromSide: "bottom", toSide: "top" },
      { from: "pre", to: "provider", fromSide: "right", toSide: "left", label: "ALLOW", via: [[1155, 482], [1155, 295]] },
      { from: "pre", to: "toolBlock", fromSide: "bottom", toSide: "top", color: COLORS.block[1], label: "BLOCK / CONFIRM" },
      { from: "provider", to: "post", fromSide: "bottom", toSide: "top" },
      { from: "post", to: "reply", fromSide: "bottom", toSide: "top" },
      { from: "post", to: "output", fromSide: "bottom", toSide: "top", color: COLORS.modify[1], label: "REDACT / BLOCK" },
      { from: "toolBlock", to: "trace", dashed: true, fromSide: "bottom", toSide: "top" },
      { from: "output", to: "trace", dashed: true, fromSide: "left", toSide: "right" },
    ],
  };

  specs.scan = {
    title: "/v1/scan scan-only 检测流水线",
    subtitle: "Proxy 不调用 LLM，只返回 ALLOW / MODIFY / BLOCK 与审计字段",
    lanes: [lane("顺序检测链", 70, 155, 1660, 390, COLORS.laneGreen), lane("决策输出", 70, 600, 1660, 245, COLORS.laneGray)],
    nodes: [
      ...cardRow(
        ["parse", "intent", "rules", "scanners", "decision", "audit"],
        ["parse_node\n消息规范化", "intent_node\n意图分类", "rules_node\ndenylist / 编码 / 长度", "parallel_scanners_node\nLLM Guard / NeMo", "decision_node\n风险聚合", "request audit\n请求审计"],
        120,
        285,
        230,
        110,
        45,
        ["runtime", "runtime", "proxy", "llm", "gate", "audit"],
        ["doc", "chip", "shield", "chip", "shield", "doc"],
      ),
      node("shared", "request-local\ndenylist_hits 共享状态", 500, 455, 320, 95, "note", "db"),
      node("allow", "ALLOW\nHTTP 200", 410, 670, 250, 110, "allow", "ok"),
      node("modify", "MODIFY\nHTTP 200", 775, 670, 250, 110, "modify", "edit"),
      node("block", "BLOCK\nHTTP 403", 1140, 670, 250, 110, "block", "stop"),
    ],
    edges: [
      { from: "parse", to: "intent" },
      { from: "intent", to: "rules" },
      { from: "rules", to: "scanners" },
      { from: "scanners", to: "decision" },
      { from: "decision", to: "audit" },
      { from: "rules", to: "shared", dashed: true, label: "共享命中" },
      { from: "intent", to: "shared", dashed: true, label: "复用命中" },
      { from: "decision", to: "allow" },
      { from: "decision", to: "modify" },
      { from: "decision", to: "block" },
    ],
  };

  specs.risk = {
    title: "风险聚合与决策规则",
    subtitle: "多类信号聚合为 risk_score，并产生可解释字段",
    lanes: [lane("风险信号", 70, 150, 1660, 260, COLORS.laneYellow), lane("聚合与路由", 70, 475, 1660, 390, COLORS.laneGray)],
    nodes: [
      ...cardRow(
        ["intent", "rules", "scanner", "pii", "boost"],
        ["Intent\n越权 / 泄露 / 注入", "Rules\ndenylist / 编码 / 长度", "Scanners\nLLM Guard / NeMo", "PII / Secrets\n敏感实体", "score_boost\n自定义风险提升"],
        150,
        240,
        260,
        112,
        55,
        ["runtime", "proxy", "llm", "gate", "audit"],
        ["chip", "shield", "chip", "shield", "doc"],
      ),
      node("score", "风险聚合\nrisk_score 0-1", 700, 510, 300, 110, "gate", "shield"),
      node("rule", "决策规则", 750, 695, 200, 140, "gate", "shield", { shape: "diamond", maxChars: 6 }),
      node("block", "BLOCK\ndenylist 或 risk >= max_risk", 390, 760, 300, 110, "block", "stop"),
      node("modify", "MODIFY\nPII mask / 参数清洗", 1040, 760, 300, 110, "modify", "edit"),
      node("allow", "ALLOW\n无高风险信号", 1360, 760, 260, 110, "allow", "ok"),
      node("explain", "解释字段\nflags / reason / intent", 1040, 520, 310, 100, "note", "doc"),
    ],
    edges: [
      { from: "intent", to: "score" },
      { from: "rules", to: "score" },
      { from: "scanner", to: "score" },
      { from: "pii", to: "score" },
      { from: "boost", to: "score" },
      { from: "score", to: "rule" },
      { from: "rule", to: "block", color: COLORS.block[1] },
      { from: "rule", to: "modify", color: COLORS.modify[1] },
      { from: "rule", to: "allow", color: COLORS.allow[1] },
      { from: "score", to: "explain", dashed: true },
    ],
  };

  specs.agent = {
    title: "Agent Runtime 运行图",
    subtitle: "按节点边界顺序执行，记录工具计划与 Trace 证据",
    lanes: [
      lane("上下文与策略解析", 70, 150, 520, 690, COLORS.laneBlue),
      lane("模型调用与工具循环", 640, 150, 540, 690, COLORS.laneYellow),
      lane("回复与证据", 1230, 150, 500, 690, COLORS.laneGray),
    ],
    nodes: [
      node("input", "input_node\n用户消息", 130, 220, 250, 95, "ingress", "msg"),
      node("context", "load_context\n历史与 runtime spec", 130, 350, 310, 95, "runtime", "doc"),
      node("role", "resolve_role\n未知显式角色 fail-closed", 130, 480, 335, 95, "gate", "shield"),
      node("policy", "policy_node\n策略与工具 allowlist", 130, 610, 325, 95, "proxy", "doc"),
      node("llm", "llm_call_node\n模型调用前 /v1/scan", 705, 220, 340, 100, "llm", "chip"),
      node("plan", "工具计划?", 775, 390, 210, 140, "gate", "shield", { shape: "diamond", maxChars: 6 }),
      node("pre", "pre_tool_gate_node\n执行前检查", 705, 600, 330, 95, "gate", "shield"),
      node("exec", "tool_executor_node\nOpenClaw provider", 830, 740, 330, 95, "provider", "tool"),
      node("post", "post_tool_gate_node\n结果清洗", 505, 740, 290, 95, "gate", "shield"),
      node("response", "response_node\n最终回复", 1285, 260, 300, 100, "audit", "doc"),
      node("memory", "memory_node\n会话记忆", 1285, 420, 300, 100, "audit", "db"),
      node("trace", "TraceAccumulator\n全链路证据", 1285, 610, 320, 100, "note", "doc"),
      node("limit", "max_iterations = 3\n避免循环调用", 1285, 745, 320, 90, "note", "shield"),
    ],
    edges: [
      { from: "input", to: "context", fromSide: "bottom", toSide: "top" },
      { from: "context", to: "role", fromSide: "bottom", toSide: "top" },
      { from: "role", to: "policy", fromSide: "bottom", toSide: "top" },
      { from: "policy", to: "llm", fromSide: "right", toSide: "left", via: [[610, 658], [610, 270]] },
      { from: "llm", to: "plan", fromSide: "bottom", toSide: "top" },
      { from: "plan", to: "pre", fromSide: "bottom", toSide: "top", label: "有工具" },
      { from: "pre", to: "exec", fromSide: "bottom", toSide: "top" },
      { from: "exec", to: "post", fromSide: "left", toSide: "right" },
      { from: "plan", to: "response", fromSide: "right", toSide: "left", label: "无工具" },
      { from: "response", to: "memory", fromSide: "bottom", toSide: "top" },
      { from: "memory", to: "trace", fromSide: "bottom", toSide: "top" },
    ],
    notes: [
      { x: 700, y: 835, w: 420, h: 70, label: "清洗后的工具结果回到模型上下文；阻断或确认路径直接生成暂停回复。", type: "note", maxChars: 25, size: 20 },
    ],
  };

  specs.preGate = {
    title: "pre-tool gate 检查链与四类决策",
    subtitle: "真实工具执行前完成 RBAC、Schema、风险、限额和确认检查",
    lanes: [lane("执行前检查", 70, 150, 1660, 350, COLORS.laneYellow), lane("门控结果", 70, 575, 1660, 275, COLORS.laneGray)],
    nodes: [
      node("plan", "模型工具计划\ntool name + args", 165, 270, 300, 110, "llm", "chip"),
      node("check", "执行前检查集合\nRBAC / Schema / Context risk\nLimits / Confirmation", 620, 245, 460, 150, "gate", "shield", { maxChars: 22 }),
      node("decision", "pre-tool decision", 1270, 250, 230, 150, "gate", "shield", { shape: "diamond", maxChars: 8 }),
      node("allow", "ALLOW\n直接执行", 230, 670, 250, 110, "allow", "ok"),
      node("modify", "MODIFY\n清洗参数后执行", 610, 670, 290, 110, "modify", "edit"),
      node("block", "BLOCK\n真实工具不执行", 990, 670, 290, 110, "block", "stop"),
      node("confirm", "REQUIRE_CONFIRMATION\n进入审批队列", 1360, 670, 330, 110, "block", "user"),
    ],
    edges: [
      { from: "plan", to: "check" },
      { from: "check", to: "decision" },
      { from: "decision", to: "allow" },
      { from: "decision", to: "modify" },
      { from: "decision", to: "block", color: COLORS.block[1] },
      { from: "decision", to: "confirm", color: COLORS.block[1] },
    ],
  };

  specs.postGate = {
    title: "post-tool gate 输出清洗流程",
    subtitle: "工具原始输出不直接进入模型上下文",
    lanes: [lane("输出检查", 70, 150, 1660, 350, COLORS.lanePurple), lane("上下文入口", 70, 575, 1660, 275, COLORS.laneGray)],
    nodes: [
      node("raw", "工具原始输出\n不可信", 180, 270, 300, 110, "provider", "tool"),
      node("check", "输出检查集合\nInjection / PII / Secrets / Size", 645, 250, 430, 135, "gate", "shield"),
      node("decision", "post-tool decision", 1285, 250, 230, 150, "gate", "shield", { shape: "diamond", maxChars: 8 }),
      node("pass", "PASS\n进入上下文", 180, 670, 250, 110, "allow", "ok"),
      node("redact", "REDACT\n脱敏后进入上下文", 555, 670, 300, 110, "modify", "edit"),
      node("truncate", "TRUNCATE\n截断后进入上下文", 940, 670, 315, 110, "modify", "edit"),
      node("block", "BLOCK\n占位符替代原结果", 1345, 670, 300, 110, "block", "stop"),
    ],
    edges: [
      { from: "raw", to: "check" },
      { from: "check", to: "decision" },
      { from: "decision", to: "pass" },
      { from: "decision", to: "redact" },
      { from: "decision", to: "truncate" },
      { from: "decision", to: "block", color: COLORS.block[1] },
    ],
  };

  specs.openclaw = {
    title: "OpenClaw provider 受保护桥接",
    subtitle: "运行时配置、CLI 执行、输出解析与 post-tool gate 回流",
    lanes: [
      lane("受保护工具配置", 70, 150, 520, 690, COLORS.laneBlue),
      lane("OpenClaw 执行", 640, 150, 520, 690, COLORS.lanePurple),
      lane("结果回流与异常处理", 1210, 150, 520, 690, COLORS.laneGray),
    ],
    nodes: [
      node("spec", "runtime spec\nprovider_type=openclaw", 135, 240, 330, 105, "runtime", "doc"),
      node("protect", "tool_protection\ngate flag 优先级", 135, 405, 330, 105, "gate", "shield"),
      node("prompt", "build_scoped_prompt\n限定 skill 与参数", 135, 570, 340, 105, "proxy", "doc"),
      node("session", "session 派生\nagent-firewall-<hash>", 150, 735, 320, 90, "note", "db"),
      node("cli", "OpenClaw CLI/runtime\nopenclaw agent ...", 720, 270, 330, 115, "provider", "terminal"),
      node("parse", "CLI 输出解析\nJSON / envelope / logs", 720, 455, 330, 115, "llm", "doc"),
      node("result", "provider result\nstdout / structured data", 720, 640, 330, 115, "provider", "tool"),
      node("post", "post-tool gate\n清洗后回流", 1290, 315, 330, 115, "gate", "shield"),
      node("error", "异常处理\ntimeout / stderr / HTTP 502", 1290, 610, 330, 115, "block", "stop"),
    ],
    edges: [
      { from: "spec", to: "protect" },
      { from: "protect", to: "prompt" },
      { from: "prompt", to: "cli" },
      { from: "session", to: "cli", dashed: true, label: "运行参数" },
      { from: "cli", to: "parse" },
      { from: "parse", to: "result" },
      { from: "result", to: "post" },
      { from: "cli", to: "error", dashed: true, color: COLORS.block[1], label: "失败" },
    ],
  };

  specs.interventionState = {
    title: "intervention 审批状态机",
    subtitle: "输入阻断、工具确认和人工审批在 Proxy 中闭环",
    lanes: [lane("状态转移", 70, 150, 1660, 670, COLORS.laneGray)],
    nodes: [
      node("trigger", "触发暂停\ninput_block / tool_block / confirmation", 170, 260, 380, 115, "block", "stop"),
      node("pending", "pending\n等待人工审批", 700, 260, 280, 115, "modify", "user"),
      node("approved", "approved\n允许重放", 1160, 230, 280, 105, "allow", "ok"),
      node("rejected", "rejected\n不重放", 1160, 390, 280, 105, "block", "stop"),
      node("check", "approved_intervention_id\n重放时复核", 700, 570, 350, 105, "note", "shield"),
      node("completed", "completed\n执行完成", 1170, 620, 270, 105, "audit", "doc"),
      node("failed", "failed\n执行失败", 360, 620, 270, 105, "block", "stop"),
    ],
    edges: [
      { from: "trigger", to: "pending" },
      { from: "pending", to: "approved", label: "批准", color: COLORS.allow[1] },
      { from: "pending", to: "rejected", label: "拒绝", color: COLORS.block[1] },
      { from: "approved", to: "check" },
      { from: "check", to: "completed" },
      { from: "approved", to: "failed", dashed: true, color: COLORS.block[1], label: "执行异常" },
    ],
  };

  specs.trace = {
    title: "Trace 审计证据链结构",
    subtitle: "回答哪一层拦截、是否执行真实工具、结果是否进入上下文",
    lanes: [
      lane("请求与输入证据", 70, 150, 520, 600, COLORS.laneBlue),
      lane("工具链证据", 640, 150, 520, 600, COLORS.laneYellow),
      lane("回复与审计", 1210, 150, 520, 600, COLORS.laneGreen),
    ],
    nodes: [
      node("meta", "请求元数据\nsession / role / policy / model", 145, 260, 350, 110, "runtime", "doc"),
      node("input", "输入扫描证据\nintent / risk / decision", 145, 480, 350, 110, "proxy", "shield"),
      node("pre", "工具计划与 pre-tool\ntool / args / checks", 725, 285, 350, 110, "gate", "shield"),
      node("post", "工具执行与 post-tool\nprovider / latency / sanitization", 705, 505, 390, 110, "provider", "tool"),
      node("reply", "最终回复\nerrors / counters", 1290, 230, 340, 105, "audit", "doc"),
      node("run", "Trace-run\n可复核证据链", 1290, 420, 340, 105, "note", "db"),
      node("answer", "审计回答\n哪层拦截 / 是否执行 / 是否入上下文", 1265, 610, 390, 115, "note", "doc"),
    ],
    edges: [
      { from: "meta", to: "input" },
      { from: "input", to: "pre" },
      { from: "pre", to: "post" },
      { from: "post", to: "reply" },
      { from: "reply", to: "run" },
      { from: "run", to: "answer" },
      { from: "input", to: "run", dashed: true },
      { from: "pre", to: "run", dashed: true },
      { from: "post", to: "run", dashed: true },
    ],
  };

  specs.interventionFlow = {
    title: "Intervention 人工审批闭环",
    subtitle: "pending 审批项由控制台处理，批准后携带审批 ID 重放",
    lanes: [lane("Approved path", 70, 155, 1660, 290, COLORS.laneGreen), lane("Rejected path", 70, 520, 1660, 250, COLORS.laneRed)],
    nodes: [
      node("pause", "暂停触发\nProxy BLOCK / 敏感工具确认", 130, 245, 340, 110, "block", "stop"),
      node("pending", "创建审批项\n/v1/interventions pending", 560, 245, 360, 110, "modify", "doc"),
      node("console", "Approvals / Audit\n本地控制台审核", 1010, 245, 340, 110, "runtime", "user"),
      node("replay", "Bridge worker\n携带 approved_intervention_id 重放", 1410, 245, 300, 110, "provider", "terminal"),
      node("runtime", "Agent Runtime\n验证审批状态并继续", 1010, 620, 360, 110, "gate", "shield"),
      node("reject", "rejected\n原请求不执行真实敏感工具", 560, 620, 360, 110, "block", "stop"),
    ],
    edges: [
      { from: "pause", to: "pending" },
      { from: "pending", to: "console" },
      { from: "console", to: "replay", label: "批准", color: COLORS.allow[1] },
      { from: "replay", to: "runtime", label: "复核" },
      { from: "console", to: "reject", label: "拒绝", color: COLORS.block[1] },
    ],
    notes: [
      { x: 190, y: 815, w: 1420, h: 84, label: "审批状态由 Proxy 保存和验证；批准只对对应 intervention 生效，不能泛化为后续任意工具调用。", type: "note", maxChars: 42 },
    ],
  };

  specs.toolState = {
    title: "工具调用门控状态机",
    subtitle: "BLOCK / REQUIRE_CONFIRMATION 在真实工具前发生，REDACT / BLOCK_OUTPUT 在上下文前发生",
    lanes: [lane("Pre-tool decision", 70, 150, 1660, 240, COLORS.laneYellow), lane("Execution after approval", 70, 455, 1660, 210, COLORS.laneGreen), lane("Post-tool decision", 70, 720, 1660, 210, COLORS.lanePurple)],
    nodes: [
      node("plan", "工具计划生成", 130, 235, 240, 95, "llm", "chip"),
      node("pre", "pre-tool 检查", 460, 235, 250, 95, "gate", "shield"),
      node("allow", "ALLOW / MODIFY", 800, 235, 260, 95, "allow", "ok"),
      node("block", "BLOCK", 1150, 235, 220, 95, "block", "stop"),
      node("confirm", "REQUIRE_CONFIRMATION", 1450, 235, 250, 95, "block", "user"),
      node("replay", "审批通过重放", 400, 525, 260, 95, "modify", "user"),
      node("exec", "工具执行", 780, 525, 250, 95, "provider", "tool"),
      node("raw", "原始输出", 1130, 525, 250, 95, "provider", "doc"),
      node("post", "post-tool 检查", 240, 790, 260, 95, "gate", "shield"),
      node("pass", "PASS", 610, 790, 210, 95, "allow", "ok"),
      node("redact", "REDACT", 900, 790, 230, 95, "modify", "edit"),
      node("outBlock", "BLOCK_OUTPUT", 1210, 790, 280, 95, "block", "stop"),
      node("trace", "Trace 落盘", 1540, 790, 190, 95, "audit", "doc"),
    ],
    edges: [
      { from: "plan", to: "pre" },
      { from: "pre", to: "allow" },
      { from: "pre", to: "block", color: COLORS.block[1] },
      { from: "pre", to: "confirm", color: COLORS.block[1] },
      { from: "confirm", to: "replay", label: "批准" },
      { from: "allow", to: "exec" },
      { from: "replay", to: "exec" },
      { from: "exec", to: "raw" },
      { from: "raw", to: "post" },
      { from: "post", to: "pass" },
      { from: "post", to: "redact" },
      { from: "post", to: "outBlock", color: COLORS.block[1] },
      { from: "pass", to: "trace", dashed: true },
      { from: "redact", to: "trace", dashed: true },
      { from: "outBlock", to: "trace", dashed: true },
    ],
  };

  specs.delegation = {
    title: "子 Agent 委派链的门控与审计",
    subtitle: "委派被视为受保护工具调用，受角色、参数、预算和输出清洗约束",
    lanes: [lane("Delegation as protected tool call", 70, 155, 1660, 290, COLORS.laneBlue), lane("Risks", 70, 515, 760, 250, COLORS.laneRed), lane("Controls", 970, 515, 760, 250, COLORS.laneGreen)],
    nodes: [
      node("main", "Main Agent\n接收任务", 135, 255, 270, 105, "runtime", "user"),
      node("gate", "Gate\n角色 / 参数 / 预算", 520, 255, 300, 105, "gate", "shield"),
      node("sub", "Subagent / Tool\nOpenClaw / MCP", 935, 255, 320, 105, "provider", "tool"),
      node("trace", "Trace\n记录委派证据", 1385, 255, 270, 105, "audit", "doc"),
      node("risk1", "低权限用户诱导\n高权限委派", 170, 610, 270, 100, "block", "stop"),
      node("risk2", "过量上下文\n发送给子 Agent", 500, 610, 270, 100, "block", "stop"),
      node("ctrl1", "RBAC / Schema", 1020, 610, 245, 100, "allow", "shield"),
      node("ctrl2", "Quotas", 1310, 610, 200, 100, "modify", "doc"),
      node("ctrl3", "Post-cleaning", 1540, 610, 160, 100, "allow", "ok"),
    ],
    edges: [
      { from: "main", to: "gate" },
      { from: "gate", to: "sub" },
      { from: "sub", to: "trace" },
      { from: "main", to: "risk1", dashed: true, color: COLORS.block[1] },
      { from: "sub", to: "risk2", dashed: true, color: COLORS.block[1] },
      { from: "gate", to: "ctrl1", dashed: true, color: COLORS.allow[1] },
      { from: "gate", to: "ctrl2", dashed: true, color: COLORS.modify[1] },
      { from: "sub", to: "ctrl3", dashed: true, color: COLORS.allow[1] },
    ],
  };

  specs.evidence = {
    title: "实验口径与证据链总览",
    subtitle: "离线确定性复核用于主要结论，本机联调用于验证真实链路连续性",
    lanes: [lane("离线确定性复核", 70, 165, 760, 560, COLORS.laneBlue), lane("本机工具链联调", 970, 165, 760, 560, COLORS.laneGreen)],
    nodes: [
      node("pytest", "pytest\n纯内存回归", 135, 270, 260, 100, "runtime", "terminal"),
      node("mock", "mock LLM\n静态红队场景", 480, 270, 270, 100, "llm", "chip"),
      node("chain", "11 agent-chain\n离线回放", 300, 505, 310, 105, "audit", "doc"),
      node("telegram", "Telegram DM\n入口适配", 1035, 270, 260, 100, "ingress", "msg"),
      node("gateway", "OpenClaw Gateway\nhealth / runtime contract", 1375, 270, 300, 100, "provider", "tool"),
      node("inter", "intervention\n审批闭环", 1050, 505, 280, 105, "gate", "user"),
      node("sqlite", "SQLite Trace\nrequest / intervention", 1410, 505, 280, 105, "audit", "db"),
      node("conclusion", "两类证据互补\n不把外部 benchmark 数值混入确定性结论", 555, 805, 700, 105, "note", "doc"),
    ],
    edges: [
      { from: "pytest", to: "mock" },
      { from: "mock", to: "chain" },
      { from: "telegram", to: "gateway" },
      { from: "gateway", to: "inter" },
      { from: "inter", to: "sqlite" },
      { from: "chain", to: "conclusion" },
      { from: "sqlite", to: "conclusion" },
    ],
  };

  return specs;
}

const SPECS = figureSpecs();

const outputs = [
  ["fig_2_1_trust_boundaries", "trust", "image"],
  ["fig_3_1_architecture", "architecture", "image"],
  ["fig_4_1_method_overview", "method", "image"],
  ["fig_4_2_scan_pipeline", "scan", "image"],
  ["fig_4_3_risk_decision", "risk", "image"],
  ["fig_4_4_agent_runtime_graph", "agent", "image"],
  ["fig_4_5_pre_tool_gate", "preGate", "image"],
  ["fig_4_6_post_tool_gate", "postGate", "image"],
  ["fig_4_7_openclaw_bridge", "openclaw", "image"],
  ["fig_4_8_intervention_state", "interventionState", "image"],
  ["fig_4_9_trace_evidence", "trace", "image"],
  ["fig_trust_boundaries", "trust", "latex"],
  ["fig_architecture", "architecture", "latex"],
  ["fig_proxy_pipeline", "scan", "latex"],
  ["fig_agent_pipeline", "agent", "latex"],
  ["fig_intervention_flow", "interventionFlow", "latex"],
  ["fig_tool_gate_state_machine", "toolState", "latex"],
  ["fig_delegation", "delegation", "latex"],
  ["fig_trace_evidence", "trace", "latex"],
  ["fig_evidence_scope", "evidence", "latex"],
];

function renderOne(slug, specKey, target) {
  const spec = SPECS[specKey];
  const svg = renderSvg(spec);
  const svgPath = path.join(SVG_DIR, `${slug}.svg`);
  const htmlPath = path.join(HTML_DIR, `${slug}.html`);
  fs.writeFileSync(svgPath, svg, "utf8");
  writeExcalidraw({ ...spec, source: SOURCE_NOTES[slug] }, slug);
  const pngPath = target === "latex" ? path.join(LATEX_FIGURE_DIR, `${slug}.png`) : path.join(IMAGE_DIR, `${slug}.png`);
  const pdfPath = target === "latex" ? path.join(LATEX_FIGURE_DIR, `${slug}.pdf`) : null;
  renderWithChrome(svgPath, htmlPath, pngPath, pdfPath);
  return { slug, target, pngPath, pdfPath, svgPath };
}

function contactSheet(rendered) {
  const articleItems = rendered.filter((item) => item.target === "image");
  const cols = 3;
  const tileW = 560;
  const tileH = 385;
  const pad = 34;
  const rows = Math.ceil(articleItems.length / cols);
  const width = cols * tileW + (cols + 1) * pad;
  const height = rows * tileH + (rows + 1) * pad;
  const tiles = articleItems
    .map((item, index) => {
      const col = index % cols;
      const row = Math.floor(index / cols);
      const x = pad + col * (tileW + pad);
      const y = pad + row * (tileH + pad);
      return `<div class="tile" style="left:${x}px;top:${y}px;width:${tileW}px;height:${tileH}px"><img src="${pathToFileURL(item.pngPath).href}"><div>${esc(item.slug)}</div></div>`;
    })
    .join("\n");
  const htmlPath = path.join(HTML_DIR, "excalidraw_contact_sheet.html");
  const pngPath = path.join(IMAGE_DIR, "excalidraw_contact_sheet.png");
  const html = `<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;width:${width}px;height:${height}px;background:#f8fafc;overflow:hidden;font-family:${FONT}}
.tile{position:absolute;background:white;border:1px solid #cbd5e1;border-radius:12px;box-sizing:border-box;overflow:hidden}
.tile img{position:absolute;left:10px;top:10px;width:${tileW - 20}px;height:${tileH - 58}px;object-fit:contain}
.tile div{position:absolute;left:18px;bottom:15px;color:${COLORS.ink};font-size:20px}
</style></head><body>${tiles}</body></html>`;
  fs.writeFileSync(htmlPath, html, "utf8");
  execFileSync(CHROME, [
    "--headless=new",
    "--disable-gpu",
    "--allow-file-access-from-files",
    "--hide-scrollbars",
    "--force-device-scale-factor=1",
    `--window-size=${width},${height}`,
    `--screenshot=${pngPath}`,
    pathToFileURL(htmlPath).href,
  ], { stdio: "ignore" });
  return pngPath;
}

function main() {
  ensureDirs();
  if (!fs.existsSync(CHROME)) {
    throw new Error(`Google Chrome not found at ${CHROME}`);
  }
  const rendered = outputs.map(([slug, specKey, target]) => renderOne(slug, specKey, target));
  const contact = contactSheet(rendered);
  for (const item of rendered) {
    console.log(`${item.target}: ${item.slug}`);
  }
  console.log(`contact_sheet: ${contact}`);
}

main();
