import fs from "node:fs/promises";
import fsSync from "node:fs";
import path from "node:path";

const ARTIFACT_TOOL =
  "/Users/isaachuo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";
const { Presentation, PresentationFile } = await import(ARTIFACT_TOOL);

const ROOT = "/Users/isaachuo/Agent-Firewall";
const WORKSPACE =
  "/Users/isaachuo/Agent-Firewall/outputs/019e26b0-70b1-7063-bd86-04eb11d4e5e9/presentations/agent-firewall-defense";
const PREVIEW_DIR = path.join(WORKSPACE, "preview");
const OUTPUT_DIR = "/Users/isaachuo/Agent-Firewall/article/PPT";
const FINAL_PPTX = path.join(OUTPUT_DIR, "Agent-Firewall-毕业论文答辩.pptx");
const SOURCE_DOCX = path.join(OUTPUT_DIR, "（4）霍玮放-本科毕业论文（设计）.docx");
const IMAGE_DIR = path.join(OUTPUT_DIR, "images");

const W = 1280;
const H = 720;

const C = {
  forest: "#2F7D4A",
  pine: "#14532D",
  leaf: "#A8D5BA",
  mint: "#F4FAF6",
  mint2: "#EAF5EE",
  white: "#FFFFFF",
  ink: "#1F2933",
  slate: "#4B5563",
  muted: "#6B7280",
  line: "#D7E5DC",
  gold: "#D8A23A",
  blue: "#2F80ED",
  danger: "#C2410C",
  amber: "#F59E0B",
  red: "#DC2626",
  gray: "#EEF2F0",
};

const FONT = "Arial Unicode MS";
const TITLE_FONT = "Arial Unicode MS";

function frame(x, y, w, h) {
  return { left: x, top: y, width: w, height: h };
}

function shape(slide, x, y, w, h, opts = {}) {
  const s = slide.shapes.add({ geometry: opts.geometry ?? "rect" });
  s.frame = frame(x, y, w, h);
  if (opts.fill !== undefined) s.fill = opts.fill;
  if (opts.line !== undefined) s.line = opts.line;
  else s.line = { fill: opts.stroke ?? C.line, width: opts.strokeWidth ?? 0 };
  if (opts.radius !== undefined) s.borderRadius = opts.radius;
  if (opts.shadow !== undefined) s.shadow = opts.shadow;
  return s;
}

function text(slide, value, x, y, w, h, opts = {}) {
  const s = shape(slide, x, y, w, h, {
    fill: opts.fill,
    line: opts.line ?? { width: 0 },
    radius: opts.radius,
  });
  s.text.set(value);
  s.text.typeface = opts.typeface ?? FONT;
  s.text.fontSize = opts.size ?? 24;
  s.text.color = opts.color ?? C.ink;
  s.text.alignment = opts.align ?? "left";
  s.text.verticalAlignment = opts.valign ?? "top";
  s.text.wrap = opts.wrap ?? "square";
  s.text.insets = opts.insets ?? { top: 6, right: 8, bottom: 6, left: 8 };
  if (opts.bold !== undefined) s.text.bold = opts.bold;
  if (opts.italic !== undefined) s.text.italic = opts.italic;
  if (opts.lineSpacing !== undefined) s.text.lineSpacing = opts.lineSpacing;
  return s;
}

function pill(slide, value, x, y, w, h, opts = {}) {
  return text(slide, value, x, y, w, h, {
    size: opts.size ?? 18,
    bold: opts.bold ?? true,
    color: opts.color ?? C.forest,
    align: "center",
    valign: "middle",
    fill: opts.fill ?? C.mint2,
    line: { fill: opts.stroke ?? C.leaf, width: 1 },
    radius: h / 2,
    insets: { top: 2, right: 10, bottom: 2, left: 10 },
  });
}

function line(slide, x, y, w, h, color = C.line) {
  return shape(slide, x, y, w, h, { fill: color, line: { width: 0 } });
}

function image(slide, file, x, y, w, h, opts = {}) {
  const ext = path.extname(file).toLowerCase();
  const mime = ext === ".jpg" || ext === ".jpeg" ? "image/jpeg" : "image/png";
  const data = fsSync.readFileSync(file).toString("base64");
  return slide.images.add({
    dataUrl: `data:${mime};base64,${data}`,
    position: frame(x, y, w, h),
    fit: opts.fit ?? "contain",
    alt: opts.alt ?? path.basename(file),
    borderRadius: opts.radius,
  });
}

function addFooter(slide, index, section) {
  line(slide, 72, 666, 1136, 1.5, C.line);
  text(slide, "Agent-Firewall 毕业论文答辩", 72, 676, 350, 22, {
    size: 13,
    color: C.muted,
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  });
  text(slide, section, 480, 676, 320, 22, {
    size: 13,
    color: C.forest,
    align: "center",
    bold: true,
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  });
  text(slide, String(index).padStart(2, "0"), 1148, 676, 60, 22, {
    size: 13,
    color: C.muted,
    align: "right",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  });
}

function addHeader(slide, kicker, title, subtitle, index, section) {
  pill(slide, kicker, 72, 48, 150, 30, { size: 14 });
  text(slide, title, 72, 88, 960, 46, {
    size: 30,
    bold: true,
    color: C.ink,
    typeface: TITLE_FONT,
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  });
  if (subtitle) {
    text(slide, subtitle, 74, 132, 900, 32, {
      size: 17,
      color: C.slate,
      insets: { top: 0, right: 0, bottom: 0, left: 0 },
    });
  }
  addFooter(slide, index, section);
}

function addNotes(slide, notes) {
  slide.speakerNotes.setText(notes.join("\n"));
}

function addSlide(p, kicker, title, section, subtitle, notes) {
  const slide = p.slides.add({ width: W, height: H });
  slide.background.fill = C.white;
  const idx = p.slides.count;
  addHeader(slide, kicker, title, subtitle, idx, section);
  addNotes(slide, notes);
  return slide;
}

function bulletList(slide, items, x, y, w, opts = {}) {
  const gap = opts.gap ?? 58;
  items.forEach((item, i) => {
    const cy = y + i * gap;
    shape(slide, x, cy + 7, 11, 11, {
      geometry: "ellipse",
      fill: opts.dot ?? C.forest,
      line: { width: 0 },
    });
    text(slide, item, x + 24, cy, w - 24, opts.itemH ?? 40, {
      size: opts.size ?? 21,
      color: opts.color ?? C.ink,
      lineSpacing: 1.13,
      insets: { top: 0, right: 0, bottom: 0, left: 0 },
    });
  });
}

function metricCard(slide, label, value, x, y, w, h, opts = {}) {
  shape(slide, x, y, w, h, {
    fill: opts.fill ?? C.mint,
    line: { fill: opts.stroke ?? C.line, width: 1 },
    radius: 8,
  });
  text(slide, value, x + 18, y + 18, w - 36, 42, {
    size: opts.valueSize ?? 30,
    bold: true,
    color: opts.valueColor ?? C.forest,
    align: opts.align ?? "left",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  });
  text(slide, label, x + 18, y + h - 40, w - 36, 26, {
    size: opts.labelSize ?? 15,
    color: opts.labelColor ?? C.slate,
    align: opts.align ?? "left",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  });
}

function node(slide, label, x, y, w, h, opts = {}) {
  shape(slide, x, y, w, h, {
    fill: opts.fill ?? C.white,
    line: { fill: opts.stroke ?? C.leaf, width: 1.5 },
    radius: opts.radius ?? 8,
  });
  if (opts.kicker) {
    text(slide, opts.kicker, x + 14, y + 10, w - 28, 18, {
      size: 11,
      bold: true,
      color: opts.kickerColor ?? C.forest,
      insets: { top: 0, right: 0, bottom: 0, left: 0 },
    });
    text(slide, label, x + 14, y + 32, w - 28, h - 42, {
      size: opts.size ?? 18,
      bold: opts.bold ?? true,
      color: opts.color ?? C.ink,
      valign: "middle",
      insets: { top: 0, right: 0, bottom: 0, left: 0 },
    });
  } else {
    text(slide, label, x + 10, y + 8, w - 20, h - 16, {
      size: opts.size ?? 18,
      bold: opts.bold ?? true,
      color: opts.color ?? C.ink,
      align: opts.align ?? "center",
      valign: "middle",
      lineSpacing: 1.1,
      insets: { top: 0, right: 0, bottom: 0, left: 0 },
    });
  }
}

function arrow(slide, x, y, w, opts = {}) {
  line(slide, x, y, w, 3, opts.color ?? C.leaf);
  text(slide, "▶", x + w - 8, y - 13, 24, 24, {
    size: 18,
    color: opts.color ?? C.leaf,
    align: "center",
    valign: "middle",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  });
}

function verticalArrow(slide, x, y, h, opts = {}) {
  line(slide, x, y, 3, h, opts.color ?? C.leaf);
  text(slide, "▼", x - 11, y + h - 6, 24, 24, {
    size: 18,
    color: opts.color ?? C.leaf,
    align: "center",
    valign: "middle",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  });
}

function progressBar(slide, label, value, max, x, y, w, color) {
  text(slide, label, x, y - 2, 155, 26, {
    size: 16,
    bold: true,
    color: C.ink,
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  });
  shape(slide, x + 170, y, w, 18, {
    fill: C.gray,
    line: { width: 0 },
    radius: 9,
  });
  shape(slide, x + 170, y, (w * value) / max, 18, {
    fill: color,
    line: { width: 0 },
    radius: 9,
  });
  text(slide, `${value}/${max}`, x + 180 + w, y - 4, 90, 28, {
    size: 15,
    color,
    bold: true,
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  });
}

function miniTable(slide, rows, x, y, widths, rowH, opts = {}) {
  const totalW = widths.reduce((a, b) => a + b, 0);
  rows.forEach((row, r) => {
    const isHead = r === 0;
    let cx = x;
    shape(slide, x, y + r * rowH, totalW, rowH, {
      fill: isHead ? opts.headerFill ?? C.forest : r % 2 === 0 ? C.white : C.mint,
      line: { fill: C.line, width: 1 },
      radius: 0,
    });
    row.forEach((cell, c) => {
      text(slide, String(cell), cx + 6, y + r * rowH + 6, widths[c] - 12, rowH - 12, {
        size: opts.size ?? 14,
        bold: isHead || c === 0,
        color: isHead ? C.white : c === 0 ? C.ink : C.slate,
        align: opts.align?.[c] ?? (c > 0 ? "center" : "left"),
        valign: "middle",
        insets: { top: 0, right: 0, bottom: 0, left: 0 },
      });
      if (c > 0) line(slide, cx, y + r * rowH, 1, rowH, C.line);
      cx += widths[c];
    });
  });
}

function donut(slide, x, y, data, opts = {}) {
  const total = data.reduce((s, d) => s + d.value, 0);
  let cy = y;
  data.forEach((d) => {
    const bw = 560;
    text(slide, d.label, x, cy - 2, 180, 24, {
      size: 15,
      bold: true,
      color: C.ink,
      insets: { top: 0, right: 0, bottom: 0, left: 0 },
    });
    shape(slide, x + 190, cy, bw, 18, {
      fill: C.gray,
      line: { width: 0 },
      radius: 9,
    });
    shape(slide, x + 190, cy, (bw * d.value) / total, 18, {
      fill: d.color,
      line: { width: 0 },
      radius: 9,
    });
    text(slide, `${d.value}`, x + 766, cy - 2, 50, 24, {
      size: 15,
      bold: true,
      color: d.color,
      align: "right",
      insets: { top: 0, right: 0, bottom: 0, left: 0 },
    });
    cy += 40;
  });
}

function addSideClaim(slide, claim, x = 832, y = 190, w = 330, h = 280) {
  shape(slide, x, y, w, h, {
    fill: C.mint,
    line: { fill: C.leaf, width: 1 },
    radius: 8,
  });
  text(slide, "答辩要点", x + 22, y + 22, w - 44, 24, {
    size: 14,
    bold: true,
    color: C.forest,
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  });
  text(slide, claim, x + 22, y + 58, w - 44, h - 78, {
    size: 22,
    bold: true,
    color: C.ink,
    lineSpacing: 1.15,
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  });
}

async function ensureClean() {
  await fs.mkdir(PREVIEW_DIR, { recursive: true });
  await fs.mkdir(OUTPUT_DIR, { recursive: true });
  const files = await fs.readdir(PREVIEW_DIR).catch(() => []);
  await Promise.all(files.map((f) => fs.rm(path.join(PREVIEW_DIR, f), { force: true })));
}

function deck() {
  const p = Presentation.create();

  // 1 Cover
  {
    const s = p.slides.add({ width: W, height: H });
    s.background.fill = C.mint;
    shape(s, 0, 0, W, H, { fill: C.mint, line: { width: 0 } });
    shape(s, 0, 0, 420, H, { fill: C.forest, line: { width: 0 } });
    shape(s, 96, 84, 86, 86, { geometry: "ellipse", fill: C.white, line: { width: 0 } });
    text(s, "BFU", 107, 108, 64, 34, {
      size: 25,
      bold: true,
      color: C.forest,
      align: "center",
      valign: "middle",
      insets: { top: 0, right: 0, bottom: 0, left: 0 },
    });
    text(s, "北京林业大学\nBeijing Forestry University", 96, 190, 255, 70, {
      size: 22,
      bold: true,
      color: C.white,
      lineSpacing: 1.2,
      insets: { top: 0, right: 0, bottom: 0, left: 0 },
    });
    line(s, 96, 288, 214, 2, C.leaf);
    text(s, "本科毕业论文答辩", 512, 96, 320, 32, {
      size: 21,
      bold: true,
      color: C.forest,
      insets: { top: 0, right: 0, bottom: 0, left: 0 },
    });
    text(s, "面向工具调用智能体的安全防火墙\nWeb 应用系统设计与实现", 506, 168, 660, 150, {
      size: 42,
      bold: true,
      color: C.ink,
      lineSpacing: 1.12,
      insets: { top: 0, right: 0, bottom: 0, left: 0 },
    });
    text(s, "Design and Implementation of a Web-based Agent Firewall for Tool-Calling AI Systems", 510, 332, 620, 44, {
      size: 17,
      color: C.slate,
      lineSpacing: 1.2,
      insets: { top: 0, right: 0, bottom: 0, left: 0 },
    });
    miniTable(
      s,
      [
        ["答辩人", "霍玮放"],
        ["学院", "信息学院（人工智能学院）"],
        ["专业", "计算机科学与技术（辅修）"],
        ["指导教师", "杨波 教授"],
        ["日期", "2026 年 6 月 3 日"],
      ],
      510,
      430,
      [120, 390],
      36,
      { size: 16, headerFill: C.forest }
    );
    addNotes(s, [
      "开场介绍论文题目和系统定位。",
      "强调这是一个围绕 OpenClaw 工具调用链路构建的本机安全防火墙 Web 应用系统。",
    ]);
  }

  // 2 Agenda
  {
    const s = addSlide(
      p,
      "目录",
      "汇报围绕问题、方案、证据和边界展开",
      "汇报结构",
      "按答辩时间压缩论文正文，只保留能够支撑结论的主线。",
      ["先讲为什么需要 Agent-Firewall，再讲系统如何实现，最后用实验和复测证明边界。"]
    );
    const items = [
      ["01", "研究背景", "工具调用智能体为什么需要模型外安全边界"],
      ["02", "系统设计", "Proxy、Agent Runtime、Frontend 与 OpenClaw 的分层"],
      ["03", "核心方法", "输入扫描、双门控、人工审批、Trace 证据链"],
      ["04", "实验结果", "策略阶梯、回放、映射评测、真实链路复测"],
      ["05", "总结展望", "主要贡献、创新点、局限与后续工作"],
    ];
    items.forEach((it, i) => {
      const y = 192 + i * 78;
      shape(s, 96, y, 78, 48, { fill: i === 0 ? C.forest : C.mint2, line: { width: 0 }, radius: 8 });
      text(s, it[0], 96, y + 7, 78, 32, {
        size: 23,
        bold: true,
        color: i === 0 ? C.white : C.forest,
        align: "center",
        valign: "middle",
        insets: { top: 0, right: 0, bottom: 0, left: 0 },
      });
      text(s, it[1], 204, y + 2, 190, 32, {
        size: 24,
        bold: true,
        color: C.ink,
        insets: { top: 0, right: 0, bottom: 0, left: 0 },
      });
      text(s, it[2], 410, y + 4, 630, 32, {
        size: 18,
        color: C.slate,
        insets: { top: 0, right: 0, bottom: 0, left: 0 },
      });
    });
  }

  // 3 Background
  {
    const s = addSlide(
      p,
      "背景",
      "工具调用让模型输出从文本变成真实操作",
      "研究背景",
      "OpenClaw、MCP 等工具生态降低了接入成本，也把攻击面推进到执行层。",
      ["本页解释研究动机：LLM 应用从问答走向能够调用工具的智能体系统。", "核心变化是模型输出可能转化为本机文件、账号或外部服务上的真实操作。"]
    );
    const xs = [92, 308, 524, 740, 956];
    const labels = [
      ["用户输入", "自然语言承载任务与攻击"],
      ["模型规划", "生成工具调用计划"],
      ["工具执行", "触达本机与外部服务"],
      ["结果回流", "工具输出进入上下文"],
      ["副作用", "可能产生真实影响"],
    ];
    labels.forEach((l, i) => {
      node(s, `${l[0]}\n${l[1]}`, xs[i], 250, 150, 92, {
        fill: i === 2 ? C.forest : C.white,
        stroke: i === 2 ? C.forest : C.leaf,
        color: i === 2 ? C.white : C.ink,
        size: 17,
      });
      if (i < labels.length - 1) arrow(s, xs[i] + 154, 294, 58);
    });
    addSideClaim(s, "安全问题不再只是“模型说了什么”，而是“模型是否驱动了未经验证的工具动作”。", 230, 438, 820, 110);
  }

  // 4 Problem
  {
    const s = addSlide(
      p,
      "问题",
      "只靠提示词拒答，无法证明工具调用经过安全校验",
      "研究背景",
      "答辩重点是把“模型自觉安全”转化为“系统可证明安全”。",
      ["提出三个核心问题：输入是否被判断，工具调用是否被校验，工具输出是否可追踪。"]
    );
    const cards = [
      ["输入进入模型前", "是否完成风险判断？", C.blue],
      ["工具执行之前", "是否经过权限、参数和确认检查？", C.forest],
      ["结果进入上下文前", "是否清洗并留下复核证据？", C.gold],
    ];
    cards.forEach((c, i) => {
      const x = 106 + i * 365;
      shape(s, x, 218, 310, 220, { fill: C.white, line: { fill: C.line, width: 1.2 }, radius: 8 });
      shape(s, x, 218, 310, 12, { fill: c[2], line: { width: 0 }, radius: 6 });
      text(s, c[0], x + 24, 260, 262, 34, { size: 20, bold: true, color: c[2] });
      text(s, c[1], x + 24, 318, 250, 72, { size: 28, bold: true, color: C.ink, lineSpacing: 1.1 });
    });
    text(s, "因此，Agent-Firewall 的目标不是替代模型，而是在模型外侧建立可执行、可审计的安全边界。", 162, 500, 956, 56, {
      size: 24,
      bold: true,
      color: C.pine,
      align: "center",
      valign: "middle",
      fill: C.mint,
      line: { fill: C.leaf, width: 1 },
      radius: 8,
    });
  }

  // 5 Goals
  {
    const s = addSlide(
      p,
      "目标",
      "系统目标可以压缩为四个关键词",
      "研究目标",
      "可控制、可审批、可追踪、可复现，是后续设计与实验的评价标准。",
      ["本页对应论文研究目标：为 OpenClaw 工具调用智能体提供本机安全防火墙 Web 应用系统。"]
    );
    const goals = [
      ["可控制", "输入与工具调用必须经过策略裁决", C.forest],
      ["可审批", "高风险输入或工具暂停进入 intervention", C.gold],
      ["可追踪", "运行图关键节点写入 Trace / Audit", C.blue],
      ["可复现", "实验场景、测试命令和口径可重复", C.pine],
    ];
    goals.forEach((g, i) => {
      const x = 102 + (i % 2) * 540;
      const y = 218 + Math.floor(i / 2) * 170;
      metricCard(s, g[1], g[0], x, y, 470, 124, {
        valueColor: g[2],
        valueSize: 34,
        fill: i % 2 === 0 ? C.mint : C.white,
      });
    });
  }

  // 6 Threat model
  {
    const s = addSlide(
      p,
      "威胁模型",
      "入口、模型计划和工具输出在门控前都不可信",
      "需求分析",
      "关键资产不仅包括 API key，也包括工具描述、参数 Schema、工具输出和 Trace 预览。",
      ["威胁模型的核心是信任边界：自然语言输入、模型生成的计划和外部工具返回内容都可能携带攻击意图。"]
    );
    node(s, "外部消息\nTelegram / Web", 88, 242, 165, 86, { fill: C.mint });
    node(s, "Proxy\n输入扫描", 338, 242, 165, 86);
    node(s, "Agent Runtime\n工具计划", 588, 242, 165, 86);
    node(s, "OpenClaw / Provider\n工具输出", 838, 242, 190, 86);
    node(s, "Trace / Audit\n证据资产", 470, 458, 230, 86, { fill: C.mint2 });
    arrow(s, 256, 284, 78);
    arrow(s, 506, 284, 78);
    arrow(s, 756, 284, 78);
    verticalArrow(s, 590, 332, 110, { color: C.gold });
    const risks = [
      "提示词注入",
      "工具滥用",
      "混淆代理",
      "间接注入",
      "凭据泄露",
      "委派链滥用",
    ];
    risks.forEach((r, i) => pill(s, r, 82 + i * 180, 548, 145, 30, { fill: C.white, stroke: C.line, color: i % 2 ? C.danger : C.forest, size: 13 }));
  }

  // 7 Requirements
  {
    const s = addSlide(
      p,
      "需求",
      "防护需求对应四类可观察行为",
      "需求分析",
      "功能不是页面清单，而是安全边界在系统中的可验证表现。",
      ["把论文中的功能需求归纳为四类：输入、工具、输出、证据。"]
    );
    const req = [
      ["输入可拦截", "外部消息进入模型前经过 /v1/scan，高风险输入 BLOCK 或进入审批"],
      ["工具可控制", "模型提出工具计划后，执行前必须经过 RBAC、Schema、风险和确认检查"],
      ["输出可清洗", "OpenClaw skill 和未来 provider 返回内容必须经过 post-tool gate"],
      ["证据可追踪", "输入扫描、工具计划、门控决策、执行和最终回复写入 Trace"],
    ];
    req.forEach((r, i) => {
      const y = 204 + i * 92;
      shape(s, 92, y, 104, 54, { fill: i % 2 ? C.white : C.mint, line: { fill: C.leaf, width: 1 }, radius: 8 });
      text(s, `0${i + 1}`, 92, y + 11, 104, 30, { size: 24, bold: true, color: C.forest, align: "center", valign: "middle" });
      text(s, r[0], 230, y + 2, 210, 32, { size: 23, bold: true, color: C.ink });
      text(s, r[1], 450, y + 4, 640, 44, { size: 17, color: C.slate, lineSpacing: 1.1 });
    });
  }

  // 8 Architecture
  {
    const s = addSlide(
      p,
      "架构",
      "Agent-Firewall 将文本安全与能力安全分层",
      "系统设计",
      "Proxy 处理模型前扫描，Agent Runtime 处理真实工具副作用边界，Frontend 负责运维与复核。",
      ["讲清楚三部分：Proxy Service、Agent Runtime、Frontend，以及 OpenClaw provider。"]
    );
    node(s, "Frontend\n攻击演练 / 审批 / Trace", 82, 250, 210, 100, { fill: C.mint, stroke: C.leaf });
    node(s, "Proxy Service\n/v1/scan / 策略 / 审计", 392, 210, 230, 110, { fill: C.white });
    node(s, "Agent Runtime\nLLM / pre-tool / post-tool", 392, 390, 230, 110, { fill: C.white });
    node(s, "OpenClaw Skills\n本机工具能力", 752, 250, 210, 100, { fill: C.mint2 });
    node(s, "SQLite\nTrace / Audit / Control Plane", 752, 430, 210, 86, { fill: C.white });
    arrow(s, 295, 294, 92);
    verticalArrow(s, 505, 324, 60, { color: C.forest });
    arrow(s, 625, 442, 122);
    verticalArrow(s, 855, 354, 70, { color: C.gold });
    text(s, "核心边界：工具调用不再从模型直接落到 OpenClaw，而是必须经过运行时门控和审计记录。", 132, 548, 980, 44, {
      size: 22,
      bold: true,
      color: C.pine,
      align: "center",
      valign: "middle",
      fill: C.mint,
      line: { fill: C.leaf, width: 1 },
      radius: 8,
    });
  }

  // 9 Protected runtime path
  {
    const s = addSlide(
      p,
      "链路",
      "受保护链路从入口到 Trace 形成闭环",
      "系统设计",
      "direct 入口只作为 Compare 对照，不属于受保护运行链路。",
      ["本页把受保护运行链路讲成一条主路径，强调 /agent/openclaw/direct 不是安全链路证据。"]
    );
    const steps = [
      "Message ingress",
      "/agent/chat",
      "/v1/scan",
      "pre-tool gate",
      "OpenClaw provider",
      "post-tool gate",
      "Trace / Audit",
    ];
    steps.forEach((st, i) => {
      const x = 70 + i * 170;
      node(s, st, x, 286, 132, 72, { fill: i === 4 ? C.mint2 : C.white, size: 15 });
      if (i < steps.length - 1) arrow(s, x + 136, 320, 36);
    });
    shape(s, 390, 420, 490, 72, { fill: "#FFF7ED", line: { fill: "#FDBA74", width: 1 }, radius: 8 });
    text(s, "Compare 对照：/agent/openclaw/direct 可调用 OpenClaw，但不产生受保护 Trace，因此不能作为安全边界证据。", 414, 438, 442, 36, {
      size: 17,
      color: C.danger,
      bold: true,
      align: "center",
      valign: "middle",
      insets: { top: 0, right: 0, bottom: 0, left: 0 },
    });
  }

  // 10 Proxy
  {
    const s = addSlide(
      p,
      "Proxy",
      "Proxy Service 在模型调用前给出 scan-only 裁决",
      "系统设计",
      "它不转发到模型，而是返回风险、标志、意图和阻断原因。",
      ["讲 Proxy 的意义：把输入扫描前置成可复用 HTTP 安全边界。"]
    );
    node(s, "HTTP 请求\nmessages / model / policy", 96, 252, 210, 88, { fill: C.mint });
    node(s, "run_pre_llm_pipeline\n规则 + scanner + 聚合", 404, 252, 250, 88);
    node(s, "安全裁决\nALLOW / MODIFY / BLOCK", 752, 252, 250, 88, { fill: C.mint2 });
    arrow(s, 310, 292, 88);
    arrow(s, 658, 292, 88);
    const outs = [
      ["/v1/scan", "scan-only 输入扫描"],
      ["interventions", "阻断/确认审批队列"],
      ["audit logs", "请求审计与策略证据"],
      ["control plane", "Agent / role / tool 元数据"],
    ];
    outs.forEach((o, i) => metricCard(s, o[1], o[0], 112 + i * 264, 444, 222, 90, { valueSize: 22, labelSize: 13, fill: i % 2 ? C.white : C.mint }));
  }

  // 11 Agent Runtime
  {
    const s = addSlide(
      p,
      "Runtime",
      "Agent Runtime 将模型计划和真实工具副作用隔开",
      "系统设计",
      "运行图中 LLM、pre-tool、provider、post-tool 和 Trace 是连续状态转移。",
      ["本页说明 Agent Runtime 不是普通转发服务，它负责把工具计划变成可门控的执行步骤。"]
    );
    const layers = [
      ["llm_call_node", "模型调用前先经 Proxy /v1/scan"],
      ["tool_plan", "模型输出工具计划，不直接执行"],
      ["pre_tool_gate", "RBAC、Schema、上下文风险、限额、确认"],
      ["provider", "OpenClaw skill / 预留 MCP provider slot"],
      ["post_tool_gate", "PII、密钥、间接注入、超长输出处理"],
      ["trace_accumulator", "记录完整运行证据链"],
    ];
    layers.forEach((l, i) => {
      const x = 100 + (i % 3) * 350;
      const y = 226 + Math.floor(i / 3) * 160;
      node(s, l[1], x, y, 270, 92, { kicker: l[0], fill: i === 2 || i === 4 ? C.mint : C.white });
    });
  }

  // 12 Frontend
  {
    const s = addSlide(
      p,
      "控制台",
      "前端把安全边界变成可演练、可审批、可复核的界面",
      "系统设计",
      "答辩只展示关键页面，不逐个解释全部截图。",
      ["前端控制台是系统可用性证据：攻击演练、审批、Trace 和工具绑定都能在页面上完成。"]
    );
    const imgs = [
      ["fig_3_3_frontend_attack_playground.png", "Attack Playground"],
      ["fig_3_9_frontend_approvals_audit.png", "Approvals / Audit"],
      ["fig_3_10_frontend_trace_audit.png", "Trace / Audit"],
      ["fig_3_8_frontend_skills_hooks.png", "Skills & Hooks"],
    ];
    imgs.forEach((im, i) => {
      const x = 86 + (i % 2) * 540;
      const y = 200 + Math.floor(i / 2) * 198;
      shape(s, x - 4, y - 4, 462, 166, { fill: C.white, line: { fill: C.line, width: 1 }, radius: 8 });
      image(s, path.join(IMAGE_DIR, im[0]), x, y, 454, 132, { fit: "cover", radius: 5 });
      text(s, im[1], x + 12, y + 136, 300, 22, { size: 15, bold: true, color: C.forest });
    });
  }

  // 13 Method overview
  {
    const s = addSlide(
      p,
      "方法",
      "核心方法是四个控制点而不是单个检测器",
      "核心方法",
      "模型前、工具前、工具后和审计复核共同构成安全边界。",
      ["从这里进入方法部分：强调系统组合，而不是单个规则或模型判断。"]
    );
    const controls = [
      ["模型前", "输入扫描", "/v1/scan"],
      ["工具前", "执行门控", "pre-tool gate"],
      ["工具后", "输出清洗", "post-tool gate"],
      ["事后复核", "证据链", "Trace / Audit"],
    ];
    controls.forEach((c, i) => {
      const x = 124 + i * 268;
      shape(s, x, 238, 192, 192, { geometry: "ellipse", fill: i % 2 ? C.white : C.mint, line: { fill: C.leaf, width: 2 } });
      text(s, c[0], x + 36, 270, 120, 26, { size: 17, bold: true, color: C.forest, align: "center" });
      text(s, c[1], x + 25, 314, 142, 40, { size: 28, bold: true, color: C.ink, align: "center", valign: "middle" });
      text(s, c[2], x + 28, 374, 136, 24, { size: 14, color: C.slate, align: "center" });
      if (i < controls.length - 1) arrow(s, x + 198, 333, 58);
    });
  }

  // 14 Scan pipeline
  {
    const s = addSlide(
      p,
      "扫描",
      "/v1/scan 将输入风险聚合为统一裁决",
      "核心方法",
      "它接收 OpenAI-compatible 请求字段，但 scan-only 不调用 LLM。",
      ["说明扫描流水线的输入和输出，重点是统一映射为 ALLOW/MODIFY/BLOCK。"]
    );
    const stages = [
      ["请求归一化", "messages / policy"],
      ["意图识别", "normal / attack / exfiltration"],
      ["规则命中", "denylist / custom rules"],
      ["扫描器节点", "PII / secrets / guardrails"],
      ["风险聚合", "score + flags"],
      ["裁决返回", "ALLOW / MODIFY / BLOCK"],
    ];
    stages.forEach((st, i) => {
      const x = 96 + (i % 3) * 350;
      const y = 222 + Math.floor(i / 3) * 150;
      node(s, st[1], x, y, 250, 80, { kicker: st[0], fill: i === 5 ? C.mint2 : C.white });
      if (i % 3 < 2) arrow(s, x + 254, y + 40, 68);
    });
    verticalArrow(s, 585, 306, 54);
  }

  // 15 Risk decision
  {
    const s = addSlide(
      p,
      "决策",
      "ALLOW、MODIFY、BLOCK 对应不同安全动作",
      "核心方法",
      "答辩时要强调 MODIFY 被 BLOCK 也计为安全边界有效，因为它没有放行敏感内容。",
      ["讲清楚决策含义：ALLOW 放行，MODIFY 清洗，BLOCK 拦截或进入审批。"]
    );
    const decisions = [
      ["ALLOW", "安全放行", "进入模型或继续运行", C.forest],
      ["MODIFY", "清洗修改", "脱敏、截断或替换", C.gold],
      ["BLOCK", "阻断处理", "返回 403 或生成审批项", C.danger],
    ];
    decisions.forEach((d, i) => {
      const x = 140 + i * 330;
      shape(s, x, 220, 270, 210, { fill: i === 0 ? C.mint : i === 1 ? "#FFF7ED" : "#FEF2F2", line: { fill: i === 0 ? C.leaf : i === 1 ? "#FDBA74" : "#FCA5A5", width: 1.5 }, radius: 8 });
      text(s, d[0], x + 24, 252, 220, 40, { size: 32, bold: true, color: d[3], align: "center" });
      text(s, d[1], x + 24, 316, 220, 30, { size: 22, bold: true, color: C.ink, align: "center" });
      text(s, d[2], x + 32, 362, 206, 44, { size: 17, color: C.slate, align: "center", lineSpacing: 1.15 });
    });
    text(s, "统计口径：MODIFY 预期被 BLOCK 时，按安全边界有效计分。", 316, 492, 648, 42, {
      size: 20,
      bold: true,
      color: C.pine,
      align: "center",
      valign: "middle",
      fill: C.mint,
      line: { fill: C.leaf, width: 1 },
      radius: 8,
    });
  }

  // 16 Pre-tool gate
  {
    const s = addSlide(
      p,
      "前置门控",
      "pre-tool gate 阻止模型计划直接驱动真实工具",
      "核心方法",
      "工具执行前检查角色、参数、上下文风险、预算和人工确认。",
      ["本页是方法重点之一，讲它连接模型计划和真实工具副作用。"]
    );
    const checks = [
      ["RBAC", "角色是否允许该工具"],
      ["Schema", "参数结构是否合规"],
      ["Context risk", "上下文是否存在外泄/注入"],
      ["Limits", "次数、预算、会话状态"],
      ["Confirmation", "高敏工具是否需要人工确认"],
    ];
    checks.forEach((c, i) => {
      const x = 86 + i * 220;
      node(s, c[1], x, 270, 172, 88, { kicker: c[0], fill: i === 4 ? "#FFF7ED" : C.white, size: 16 });
      if (i < checks.length - 1) arrow(s, x + 176, 312, 38);
    });
    const outs = [
      ["ALLOW", C.forest],
      ["MODIFY", C.gold],
      ["BLOCK", C.danger],
      ["REQUIRE_CONFIRMATION", C.blue],
    ];
    outs.forEach((o, i) => pill(s, o[0], 190 + i * 225, 466, 190, 34, { color: o[1], fill: C.white, stroke: C.line, size: 13 }));
  }

  // 17 Post-tool gate
  {
    const s = addSlide(
      p,
      "后置门控",
      "post-tool gate 决定工具输出是否能进入上下文",
      "核心方法",
      "它处理 PII、密钥、连接串、间接注入和超长输出。",
      ["强调工具返回内容也不可信，不能原样进入模型上下文。"]
    );
    node(s, "工具原始输出\nuntrusted result", 104, 270, 210, 90, { fill: C.mint });
    node(s, "PII / secrets\n检测与脱敏", 396, 226, 210, 76);
    node(s, "间接注入\n阻断隐藏指令", 396, 364, 210, 76);
    node(s, "截断/替换\n长度与预览治理", 688, 294, 210, 76, { fill: C.white });
    node(s, "安全上下文\nsanitized result", 972, 270, 190, 90, { fill: C.mint2 });
    arrow(s, 318, 314, 72);
    arrow(s, 610, 314, 72);
    arrow(s, 902, 314, 62);
    text(s, "关键原则：工具结果必须先被清洗，再进入后续模型上下文或最终回复。", 176, 500, 928, 48, {
      size: 23,
      bold: true,
      color: C.pine,
      align: "center",
      valign: "middle",
      fill: C.mint,
      line: { fill: C.leaf, width: 1 },
      radius: 8,
    });
  }

  // 18 Intervention
  {
    const s = addSlide(
      p,
      "审批",
      "intervention 把高风险动作变成可恢复状态机",
      "核心方法",
      "输入阻断、工具阻断和工具确认都能进入统一审批队列。",
      ["讲人机协同：不是所有风险都简单拒绝，高敏工具可暂停等待审批。"]
    );
    const states = [
      ["created", "创建审批项"],
      ["pending", "等待人工处理"],
      ["approved", "携带 approved_intervention_id 重放"],
      ["rejected", "拒绝后不执行"],
    ];
    states.forEach((st, i) => {
      const x = 120 + i * 270;
      node(s, `${st[0]}\n${st[1]}`, x, 280, 190, 84, { fill: i === 2 ? C.mint2 : C.white, size: 16 });
      if (i < states.length - 1) arrow(s, x + 194, 320, 72, { color: i === 1 ? C.gold : C.leaf });
    });
    const kinds = ["input_block", "tool_block", "tool_confirmation"];
    kinds.forEach((k, i) => pill(s, k, 245 + i * 260, 450, 220, 34, { fill: C.mint, stroke: C.leaf, color: C.forest, size: 14 }));
  }

  // 19 Trace
  {
    const s = addSlide(
      p,
      "证据链",
      "Trace 让一次请求的安全路径可复核",
      "核心方法",
      "Trace-run 记录输入扫描、工具计划、门控决策、执行结果、后置清洗和最终回复。",
      ["这是系统的证明机制：安全边界不只是在代码里，还能在 Trace 中被老师复核。"]
    );
    const events = [
      ["input_scan", "风险分数 / flags / reason"],
      ["tool_plan", "模型提出的工具调用"],
      ["pre_tool_decision", "RBAC / schema / limits"],
      ["tool_execution", "provider / args / latency"],
      ["post_tool_decision", "redact / block / truncate"],
      ["final_reply", "最终回复与状态"],
    ];
    events.forEach((e, i) => {
      const y = 196 + i * 60;
      text(s, e[0], 150, y, 220, 28, { size: 17, bold: true, color: C.forest });
      text(s, e[1], 398, y, 620, 28, { size: 17, color: C.slate });
      line(s, 126, y + 33, 880, 1, C.line);
      shape(s, 112, y + 6, 14, 14, { geometry: "ellipse", fill: i % 2 ? C.gold : C.forest, line: { width: 0 } });
    });
    image(s, path.join(IMAGE_DIR, "fig_3_10_frontend_trace_audit.png"), 910, 212, 250, 220, { fit: "cover", radius: 6 });
  }

  // 20 Experiment design
  {
    const s = addSlide(
      p,
      "实验设计",
      "实验口径同时覆盖项目回归、链路回放和真实复测",
      "实验结果",
      "358 个 JSON 场景是主实验分母，147 个 YAML 场景作为独立场景资产说明。",
      ["讲清楚数据口径，避免把项目回归场景和公开 benchmark 混在一起。"]
    );
    metricCard(s, "JSON 项目回归场景", "358", 118, 228, 220, 116, { valueSize: 42 });
    metricCard(s, "YAML 独立场景资产", "147", 390, 228, 220, 116, { valueSize: 42, fill: C.white });
    metricCard(s, "公开基准映射场景", "40", 662, 228, 220, 116, { valueSize: 42 });
    metricCard(s, "本机 OpenClaw/Telegram 小样本", "复测", 934, 228, 220, 116, { valueSize: 36, fill: C.white });
    bulletList(
      s,
      [
        "主实验：playground.json + agent.json，覆盖输入层和工具调用语境",
        "Agent 层测试：pre-tool、post-tool、RBAC、运行图",
        "工具链回放：跨工具计划、审批重放、输出清洗和 Trace 连续状态",
        "真实复测：受保护 /agent/chat 与 direct 对照区分",
      ],
      156,
      414,
      950,
      { size: 20, gap: 48 }
    );
  }

  // 21 Data distribution
  {
    const s = addSlide(
      p,
      "数据分布",
      "主实验以攻击/敏感样本为主，并保留安全放行样本",
      "实验结果",
      "358 个场景中包含 322 个预期 BLOCK、16 个预期 MODIFY 和 20 个预期 ALLOW。",
      ["本页用数据说明样本构成，回答为什么 direct baseline 只有 20/358。"]
    );
    donut(
      s,
      116,
      230,
      [
        { label: "预期 BLOCK", value: 322, color: C.danger },
        { label: "预期 MODIFY", value: 16, color: C.gold },
        { label: "预期 ALLOW", value: 20, color: C.forest },
      ]
    );
    addSideClaim(s, "direct 不执行系统级阻断或清洗，因此只能在 20 个安全 ALLOW 样本上符合预期。", 842, 220, 300, 190);
    const cats = ["Prompt Injection", "Tool Abuse", "PII / Secrets", "Obfuscation", "Multi-Language", "RAG Poisoning", "Confused Deputy"];
    cats.forEach((c, i) => pill(s, c, 118 + (i % 4) * 250, 484 + Math.floor(i / 4) * 44, 215, 30, { size: 12, fill: C.white, stroke: C.line }));
  }

  // 22 Strategy ladder
  {
    const s = addSlide(
      p,
      "策略阶梯",
      "从未保护直连到 paranoid，正确场景数显著提升",
      "实验结果",
      "docx 口径：direct 20/358，fast 327/358，balanced/strict 331/358，paranoid 344/358。",
      ["这是实验部分最重要的一页，注意强调 balanced 到 strict 持平，paranoid 继续减少漏报。"]
    );
    const values = [
      ["direct", 20, C.muted],
      ["fast", 327, C.leaf],
      ["balanced", 331, C.forest],
      ["strict", 331, C.blue],
      ["paranoid", 344, C.gold],
    ];
    const chartX = 126;
    const chartY = 196;
    const barW = 118;
    const maxH = 280;
    values.forEach((v, i) => {
      const x = chartX + i * 192;
      const h = (v[1] / 358) * maxH;
      shape(s, x, chartY + maxH - h, barW, h, { fill: v[2], line: { width: 0 }, radius: 6 });
      text(s, String(v[1]), x, chartY + maxH - h - 34, barW, 26, { size: 20, bold: true, color: v[2], align: "center" });
      text(s, v[0], x - 20, chartY + maxH + 20, barW + 40, 24, { size: 17, bold: true, color: C.ink, align: "center" });
    });
    line(s, chartX - 26, chartY + maxH, 920, 2, C.line);
    text(s, "场景总数：358", 906, 214, 180, 28, { size: 15, color: C.muted, align: "right" });
    shape(s, 262, 570, 300, 58, { fill: "#FEF2F2", line: { fill: "#FCA5A5", width: 1 }, radius: 8 });
    text(s, "27", 286, 584, 54, 28, { size: 24, bold: true, color: C.danger, align: "center", valign: "middle" });
    text(s, "balanced / strict\n剩余未符合预期", 352, 580, 170, 36, { size: 13, color: C.slate, align: "center", valign: "middle", lineSpacing: 1.05 });
    shape(s, 688, 570, 300, 58, { fill: "#FFF7ED", line: { fill: "#FDBA74", width: 1 }, radius: 8 });
    text(s, "14", 712, 584, 54, 28, { size: 24, bold: true, color: C.gold, align: "center", valign: "middle" });
    text(s, "paranoid\n剩余未符合预期", 780, 580, 160, 36, { size: 13, color: C.slate, align: "center", valign: "middle", lineSpacing: 1.05 });
  }

  // 23 Agent tests
  {
    const s = addSlide(
      p,
      "单元测试",
      "125 个 Agent 层门控测试全部通过",
      "实验结果",
      "覆盖 pre-tool、post-tool、RBAC 和运行图行为。",
      ["强调这是基础正确性证据，不是只看端到端效果。"]
    );
    metricCard(s, "Agent 核心门控测试", "125 / 125", 108, 222, 350, 150, { valueSize: 42 });
    const rows = [
      ["测试文件", "覆盖内容"],
      ["test_pre_tool_gate.py", "RBAC、参数注入、上下文外泄、限额、确认流"],
      ["test_post_tool_gate.py", "邮箱、电话、SSN、信用卡、IP、密钥、间接注入、截断"],
      ["test_rbac.py", "角色继承、scope、默认拒绝、敏感工具确认"],
      ["test_graph.py", "运行图、问候流程、工具计划、普通用户密钥访问拦截"],
    ];
    miniTable(s, rows, 520, 210, [220, 430], 52, { size: 13 });
    text(s, "结论：工具执行前后的基础安全机制在纯内存单元测试中稳定。", 130, 464, 950, 44, {
      size: 23,
      bold: true,
      color: C.pine,
      align: "center",
      valign: "middle",
      fill: C.mint,
      line: { fill: C.leaf, width: 1 },
      radius: 8,
    });
  }

  // 24 Chain replay
  {
    const s = addSlide(
      p,
      "链路回放",
      "11 个工具链离线回放验证连续状态转移",
      "实验结果",
      "回放不调用外部 LLM 或真实工具，而是复用门控节点与 TraceAccumulator。",
      ["讲回放的价值：验证跨工具计划、执行前门控、执行后清洗和 Trace 记录。"]
    );
    metricCard(s, "工具链离线回放", "11 / 11", 98, 216, 270, 120, { valueSize: 42, fill: C.mint });
    const chains = [
      ["正常多工具", "ALLOW → PASS"],
      ["RBAC 部分拦截", "ALLOW + BLOCK"],
      ["参数注入", "BLOCK"],
      ["上下文外泄", "BLOCK"],
      ["高敏确认", "REQUIRE_CONFIRMATION"],
      ["审批后重放", "ALLOW → REDACT"],
      ["间接注入", "ALLOW → BLOCK"],
      ["委派清洗", "ALLOW → REDACT"],
    ];
    chains.forEach((c, i) => {
      const x = 420 + (i % 2) * 330;
      const y = 206 + Math.floor(i / 2) * 80;
      node(s, `${c[0]}\n${c[1]}`, x, y, 275, 58, { fill: i % 2 ? C.white : C.mint, size: 15 });
    });
    image(s, path.join(IMAGE_DIR, "fig_5_5_chain_replay_matrix.png"), 108, 390, 270, 170, { fit: "contain", radius: 6 });
  }

  // 25 Mapped benchmark
  {
    const s = addSlide(
      p,
      "映射评测",
      "40 条公开基准启发场景在受保护链路上完成执行",
      "实验结果",
      "36/40 通过，15 条输入层阻断，且无真实工具执行。",
      ["强调这不是官方 benchmark 分数，而是本项目可执行映射场景。"]
    );
    metricCard(s, "通过场景", "36 / 40", 96, 220, 210, 112, { valueSize: 38 });
    metricCard(s, "简单得分", "90", 336, 220, 170, 112, { valueSize: 38, fill: C.white });
    metricCard(s, "输入层阻断", "15", 536, 220, 190, 112, { valueSize: 38 });
    metricCard(s, "真实工具执行", "0", 756, 220, 190, 112, { valueSize: 38, fill: C.white, valueColor: C.danger });
    image(s, path.join(IMAGE_DIR, "fig_5_7_frontend_benchmark_result.png"), 94, 378, 370, 210, { fit: "cover", radius: 6 });
    addSideClaim(s, "4 个失败均为拒绝或安全解释中回显攻击标记，反映的是输出回显治理不足，而非真实工具副作用。", 540, 394, 430, 160);
  }

  // 26 OpenClaw / Telegram
  {
    const s = addSlide(
      p,
      "真实复测",
      "OpenClaw/Telegram 小样本证明受保护 provider 闭环",
      "实验结果",
      "安全摘要请求会进入 provider；泄露 system prompt/API key 请求在模型前被阻断。",
      ["注意如实说明：真实链路复测只覆盖 openclaw_summarize 和输入阻断，不能外推到所有高敏 skill。"]
    );
    const rows = [
      ["编号", "入口", "关键结果", "安全含义"],
      ["OC-01", "/agent/chat", "ALLOW，openclaw_summarize，10279 ms", "完整经过 scan、pre、provider、post、Trace"],
      ["OC-02", "/agent/chat", "BLOCK，risk_score=1.0，66 ms", "输入层阻断，无工具执行"],
      ["OC-03", "direct", "HTTP 200，5536 ms", "Compare 对照，不产生受保护 Trace"],
      ["TG-01", "Telegram", "ALLOW，REDACT，8698 ms", "真实入口进入 OpenClaw skill 链路"],
      ["TG-02", "Telegram", "BLOCK，47 ms", "泄露请求在模型调用前阻断"],
    ];
    miniTable(s, rows, 76, 204, [76, 120, 360, 520], 48, { size: 12 });
    image(s, path.join(IMAGE_DIR, "fig_5_6_openclaw_rerun.png"), 842, 518, 256, 84, { fit: "contain", radius: 6 });
  }

  // 27 Limitations
  {
    const s = addSlide(
      p,
      "边界",
      "剩余问题集中在检测信号和长期状态建模",
      "总结展望",
      "这些局限是后续工作，不应在答辩中回避。",
      ["本页如实讲局限，体现对系统能力边界的把握。"]
    );
    const limits = [
      ["语义检测", "自然语言密钥描述、社会工程话术、Prompt Injection 变体"],
      ["多语言与混淆", "ROT13、Caesar、反向文本、Leetspeak、Unicode 混淆"],
      ["多轮状态", "低慢诱导、长期记忆污染、跨会话策略漂移"],
      ["输出回显", "拒绝解释中仍可能复述攻击标记或危险命令"],
      ["MCP 真实链路", "尚未验证外部 MCP server 的身份、授权和输出清洗"],
    ];
    limits.forEach((l, i) => {
      const y = 192 + i * 76;
      pill(s, l[0], 106, y, 150, 32, { color: i === 4 ? C.blue : C.forest, fill: i % 2 ? C.white : C.mint });
      text(s, l[1], 286, y + 1, 820, 34, { size: 18, color: C.ink, valign: "middle" });
    });
    text(s, "当前 balanced 剩余 27 个未符合预期场景；paranoid 剩余 14 个。", 212, 590, 780, 42, {
      size: 22,
      bold: true,
      color: C.danger,
      align: "center",
      valign: "middle",
      fill: "#FEF2F2",
      line: { fill: "#FCA5A5", width: 1 },
      radius: 8,
    });
  }

  // 28 Closing
  {
    const s = p.slides.add({ width: W, height: H });
    s.background.fill = C.forest;
    shape(s, 0, 0, W, H, { fill: C.forest, line: { width: 0 } });
    shape(s, 820, -120, 540, 540, { geometry: "ellipse", fill: "#3F9D63", line: { width: 0 } });
    shape(s, 930, 330, 460, 460, { geometry: "ellipse", fill: "#246D40", line: { width: 0 } });
    text(s, "总结", 96, 86, 120, 36, { size: 24, bold: true, color: C.leaf });
    text(s, "Agent-Firewall 将工具调用智能体的安全边界\n从“模型自觉拒答”推进到“系统可证明门控”", 96, 158, 830, 120, {
      size: 38,
      bold: true,
      color: C.white,
      lineSpacing: 1.15,
      insets: { top: 0, right: 0, bottom: 0, left: 0 },
    });
    const finalPoints = [
      "模型前输入扫描、工具前后双门控、人工审批和 Trace 证据链形成闭环",
      "OpenClaw skill、预留 MCP provider slot 和子 Agent 委派统一建模为受保护能力",
      "通过项目回归、工具链回放、映射评测和真实链路复测建立可复现实验证据",
    ];
    finalPoints.forEach((pt, i) => {
      shape(s, 106, 338 + i * 74, 12, 12, { geometry: "ellipse", fill: C.leaf, line: { width: 0 } });
      text(s, pt, 136, 326 + i * 74, 780, 42, { size: 20, color: C.white, lineSpacing: 1.12 });
    });
    text(s, "谢谢各位老师，请批评指正", 96, 608, 520, 44, { size: 30, bold: true, color: C.white });
    text(s, "霍玮放  |  信息学院（人工智能学院）", 96, 656, 520, 24, { size: 16, color: C.leaf });
    addNotes(s, ["总结全文，回到研究问题：工具调用智能体需要模型外安全边界。", "感谢老师，进入提问环节。"]);
  }

  return p;
}

async function saveJsonNotes(p) {
  const notes = p.slides.items.map((s, i) => ({
    slide: i + 1,
    notes: s.speakerNotes.text,
  }));
  await fs.writeFile(path.join(WORKSPACE, "speaker-notes.json"), JSON.stringify(notes, null, 2), "utf8");
}

async function saveSourceNotes() {
  const data = {
    taskMode: "create",
    primaryDeckProfile: "engineering-platform",
    sourceOfTruth: SOURCE_DOCX,
    outputPptx: FINAL_PPTX,
    figures: IMAGE_DIR,
    metrics: {
      mainJsonScenarios: 358,
      expectedBlock: 322,
      expectedModify: 16,
      expectedAllow: 20,
      yamlAssets: 147,
      directScore: "20/358",
      fastScore: "327/358",
      balancedScore: "331/358",
      strictScore: "331/358",
      paranoidScore: "344/358",
      agentGateTests: "125/125",
      chainReplay: "11/11",
      mappedBenchmark: "36/40",
      mappedInputBlocks: 15,
      mappedToolExecutions: 0,
    },
    visualSystem: {
      primary: C.forest,
      light: C.mint,
      accentGold: C.gold,
      accentBlue: C.blue,
      font: FONT,
      logoPolicy: "No unofficial BFU emblem was recreated; text identity is used.",
    },
  };
  await fs.writeFile(path.join(WORKSPACE, "source-notes.json"), JSON.stringify(data, null, 2), "utf8");
}

async function exportPreviews(p) {
  for (const [i, slide] of p.slides.items.entries()) {
    const blob = await slide.export({ format: "png", scale: 1 });
    await fs.writeFile(
      path.join(PREVIEW_DIR, `slide-${String(i + 1).padStart(2, "0")}.png`),
      Buffer.from(await blob.arrayBuffer())
    );
  }
}

async function main() {
  await ensureClean();
  const p = deck();
  await saveSourceNotes();
  await saveJsonNotes(p);
  const pptx = await PresentationFile.exportPptx(p);
  await pptx.save(FINAL_PPTX);
  await exportPreviews(p);
  console.log(JSON.stringify({ slides: p.slides.count, pptx: FINAL_PPTX, previewDir: PREVIEW_DIR }, null, 2));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
