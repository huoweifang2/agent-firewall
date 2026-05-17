#!/usr/bin/env python3
"""Build the Beijing Forestry University thesis DOCX from the LaTeX draft.

The script intentionally avoids Pandoc so the generated DOCX is deterministic
and can be checked by inspecting OOXML. It uses the project LaTeX manuscript as
the content source, then applies the university format requirements through
Word styles, sections, headers/footers, page numbering, tables, and a TOC field.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import textwrap
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Mm, Pt
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
LATEX_DIR = ROOT / "latex"
TEX_PATH = LATEX_DIR / "article.tex"
DOCX_DIR = ROOT / "docx"
FIGURE_DIR = DOCX_DIR / "generated_figures"
OUT_PATH = DOCX_DIR / "霍玮放-本科毕业论文（设计）.docx"
FIGURE_SCRIPT = DOCX_DIR / "generate_publication_figures.py"
THESIS_VENV_PYTHON = DOCX_DIR / ".thesis-venv" / "bin" / "python"
GRAPHIC_SEARCH_DIRS = [
    LATEX_DIR / "figures",
]
LATEX_FIGURE_RENDER_DIR = FIGURE_DIR / "latex_figures"

TITLE_CN = "面向工具调用智能体的安全防火墙Web应用系统设计与实现"
TITLE_EN = "Design and Implementation of a Web-based Agent Firewall for Tool-Calling AI Systems"
AUTHOR = "霍玮放"
COLLEGE = "工学院"
MAJOR = "电气工程及其自动化（辅修）"
CLASS_NAME = "电气24-3"
STUDENT_ID = "230206108"
SUPERVISOR = "杨波  教授"
DATE_TEXT = "2026年5月"

PAGE_WIDTH_DXA = int(155 * 56.7)  # A4 width minus 30 mm + 25 mm margins.


def get_style_ppr(style):
    style_elm = style._element
    ppr = style_elm.find(qn("w:pPr"))
    if ppr is None:
        ppr = OxmlElement("w:pPr")
        rpr = style_elm.find(qn("w:rPr"))
        if rpr is not None:
            style_elm.insert(style_elm.index(rpr), ppr)
        else:
            style_elm.append(ppr)
    return ppr


def set_ppr_indent(
    ppr,
    *,
    first_line_chars: int | None = None,
    left_chars: int | None = None,
    hanging_chars: int | None = None,
    clear=True,
):
    ind = ppr.find(qn("w:ind"))
    if ind is None:
        ind = OxmlElement("w:ind")
        ppr.append(ind)
    if clear:
        for attr in ("firstLine", "firstLineChars", "hanging", "hangingChars", "left", "leftChars", "start", "startChars"):
            ind.attrib.pop(qn("w:" + attr), None)
    if first_line_chars is not None:
        ind.set(qn("w:firstLineChars"), str(first_line_chars))
    if left_chars is not None:
        ind.set(qn("w:leftChars"), str(left_chars))
    if hanging_chars is not None:
        ind.set(qn("w:hangingChars"), str(hanging_chars))


def set_style_indent(style, **kwargs):
    set_ppr_indent(get_style_ppr(style), **kwargs)


def set_paragraph_indent(paragraph, **kwargs):
    set_ppr_indent(paragraph._p.get_or_add_pPr(), **kwargs)


def set_paragraph_spacing(paragraph, *, before=None, after=None, line=1.25):
    pf = paragraph.paragraph_format
    if before is not None:
        pf.space_before = Pt(before)
    if after is not None:
        pf.space_after = Pt(after)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = line


def set_run_font(run, east_asia="宋体", ascii_font="Times New Roman", size=None, bold=None):
    run.font.name = ascii_font
    run._element.rPr.rFonts.set(qn("w:eastAsia"), east_asia)
    run._element.rPr.rFonts.set(qn("w:ascii"), ascii_font)
    run._element.rPr.rFonts.set(qn("w:hAnsi"), ascii_font)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold


def set_style_font(style, east_asia="宋体", ascii_font="Times New Roman", size=12, bold=False):
    style.font.name = ascii_font
    style._element.rPr.rFonts.set(qn("w:eastAsia"), east_asia)
    style._element.rPr.rFonts.set(qn("w:ascii"), ascii_font)
    style._element.rPr.rFonts.set(qn("w:hAnsi"), ascii_font)
    style.font.size = Pt(size)
    style.font.bold = bold


def set_paragraph_format(style, *, first_line_chars=0, alignment=None, before=0, after=0, line=1.25):
    pf = style.paragraph_format
    pf.first_line_indent = None
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = line
    if alignment is not None:
        pf.alignment = alignment
    if first_line_chars:
        set_style_indent(style, first_line_chars=first_line_chars * 100)


def set_outline_level(style, level: int):
    ppr = get_style_ppr(style)
    outline = ppr.find(qn("w:outlineLvl"))
    if outline is None:
        outline = OxmlElement("w:outlineLvl")
        ppr.append(outline)
    outline.set(qn("w:val"), str(level))


def set_paragraph_outline_level(paragraph, level: int):
    ppr = paragraph._p.get_or_add_pPr()
    outline = ppr.find(qn("w:outlineLvl"))
    if outline is None:
        outline = OxmlElement("w:outlineLvl")
        ppr.append(outline)
    outline.set(qn("w:val"), str(level))


def add_bottom_border(paragraph, *, size=4):
    ppr = paragraph._p.get_or_add_pPr()
    pbdr = ppr.find(qn("w:pBdr"))
    if pbdr is None:
        pbdr = OxmlElement("w:pBdr")
        ppr.append(pbdr)
    bottom = pbdr.find(qn("w:bottom"))
    if bottom is None:
        bottom = OxmlElement("w:bottom")
        pbdr.append(bottom)
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "000000")


def configure_styles(doc: Document):
    styles = doc.styles

    normal = styles["Normal"]
    set_style_font(normal, "宋体", "Times New Roman", 12, False)
    set_paragraph_format(normal, first_line_chars=2, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY)

    for name, east, ascii_font, size, bold, align, first in [
        ("Thesis Title CN", "宋体", "Times New Roman", 16, True, WD_ALIGN_PARAGRAPH.CENTER, 0),
        ("Thesis Title EN", "Times New Roman", "Times New Roman", 14, True, WD_ALIGN_PARAGRAPH.CENTER, 0),
        ("Thesis Cover Field", "宋体", "Times New Roman", 14, False, WD_ALIGN_PARAGRAPH.CENTER, 0),
        ("Thesis Heading 1", "宋体", "Times New Roman", 16, True, WD_ALIGN_PARAGRAPH.CENTER, 0),
        ("Thesis Heading 2", "宋体", "Times New Roman", 14, True, WD_ALIGN_PARAGRAPH.LEFT, 0),
        ("Thesis Heading 3", "宋体", "Times New Roman", 12, True, WD_ALIGN_PARAGRAPH.LEFT, 0),
        ("Thesis Front Heading 1", "宋体", "Times New Roman", 16, True, WD_ALIGN_PARAGRAPH.CENTER, 0),
        ("Thesis Front Heading 2", "宋体", "Times New Roman", 14, True, WD_ALIGN_PARAGRAPH.LEFT, 0),
        ("Thesis Abstract CN", "楷体-简", "Times New Roman", 12, False, WD_ALIGN_PARAGRAPH.JUSTIFY, 2),
        ("Thesis Abstract EN", "Times New Roman", "Times New Roman", 12, False, WD_ALIGN_PARAGRAPH.JUSTIFY, 2),
        ("Thesis Keyword", "宋体", "Times New Roman", 12, False, WD_ALIGN_PARAGRAPH.LEFT, 0),
        ("Thesis Caption", "宋体", "Times New Roman", 9, True, WD_ALIGN_PARAGRAPH.CENTER, 0),
        ("Thesis Table", "宋体", "Times New Roman", 9, False, WD_ALIGN_PARAGRAPH.LEFT, 0),
        ("Thesis TOC", "宋体", "Times New Roman", 10.5, False, WD_ALIGN_PARAGRAPH.LEFT, 0),
        ("Thesis Reference", "宋体", "Times New Roman", 10.5, False, WD_ALIGN_PARAGRAPH.LEFT, 0),
        ("Thesis Acknowledgement", "宋体", "Times New Roman", 10.5, False, WD_ALIGN_PARAGRAPH.JUSTIFY, 2),
        ("Thesis Code", "Menlo", "Menlo", 9, False, WD_ALIGN_PARAGRAPH.LEFT, 0),
    ]:
        style = styles.add_style(name, 1)
        set_style_font(style, east, ascii_font, size, bold)
        set_paragraph_format(
            style,
            first_line_chars=first,
            alignment=align,
            before=7.8 if name.startswith(("Thesis Heading", "Thesis Front Heading")) else 0,
            after=7.8 if name.startswith(("Thesis Heading", "Thesis Front Heading")) else 0,
            line=1.25,
        )
        if name in {"Thesis Heading 1", "Thesis Heading 2", "Thesis Heading 3"}:
            set_outline_level(style, {"Thesis Heading 1": 0, "Thesis Heading 2": 1, "Thesis Heading 3": 2}[name])

    configure_toc_styles(styles)
    set_style_indent(styles["Thesis Reference"], left_chars=202, hanging_chars=202)


def configure_toc_styles(styles):
    for name, left_chars, bold in [
        ("TOC 1", None, True),
        ("TOC 2", 100, False),
        ("TOC 3", 100, False),
    ]:
        try:
            style = styles[name]
        except KeyError:
            continue
        set_style_font(style, "宋体", "Times New Roman", 10.5, bold)
        set_paragraph_format(style, alignment=WD_ALIGN_PARAGRAPH.LEFT, before=0, after=0, line=1.25)
        set_style_indent(style, left_chars=left_chars or 0, first_line_chars=0)


def configure_section(section, page_fmt: str | None = None, start: int | None = None, header=True):
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.top_margin = Mm(30)
    section.bottom_margin = Mm(25)
    section.left_margin = Mm(30)
    section.right_margin = Mm(25)
    section.header_distance = Mm(15)
    section.footer_distance = Mm(15)
    sect_pr = section._sectPr
    pg_num = sect_pr.find(qn("w:pgNumType"))
    if pg_num is None:
        pg_num = OxmlElement("w:pgNumType")
        sect_pr.append(pg_num)
    if page_fmt:
        pg_num.set(qn("w:fmt"), page_fmt)
    if start is not None:
        pg_num.set(qn("w:start"), str(start))
    clear_header_footer(section)
    if header:
        add_header_footer(section)


def clear_header_footer(section):
    section.header.is_linked_to_previous = False
    section.footer.is_linked_to_previous = False
    for part in (section.header, section.footer):
        for paragraph in part.paragraphs:
            paragraph._element.getparent().remove(paragraph._element)


def add_field(paragraph, instr: str, placeholder: str = ""):
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    run._r.append(fld_begin)
    instr_run = paragraph.add_run()
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = instr
    instr_run._r.append(instr_text)
    sep_run = paragraph.add_run()
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    sep_run._r.append(fld_sep)
    if placeholder:
        paragraph.add_run(placeholder)
    end_run = paragraph.add_run()
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    end_run._r.append(fld_end)


def add_header_footer(section):
    hp = section.header.add_paragraph()
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_bottom_border(hp)
    run = hp.add_run("北京林业大学本科毕业论文")
    set_run_font(run, "宋体", "Times New Roman", 9)

    fp = section.footer.add_paragraph()
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_field(fp, "PAGE")
    for run in fp.runs:
        set_run_font(run, "宋体", "Times New Roman", 10.5)


def add_page_break(doc: Document):
    paragraph = doc.add_paragraph()
    paragraph.add_run().add_break(WD_BREAK.PAGE)


def add_center(doc: Document, text: str, style_name: str = "Normal", size=None, bold=None, before=0, after=0):
    paragraph = doc.add_paragraph(style=style_name)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(before)
    paragraph.paragraph_format.space_after = Pt(after)
    run = paragraph.add_run(text)
    if size is not None or bold is not None:
        set_run_font(run, "宋体", "Times New Roman", size=size, bold=bold)
    return paragraph


def add_body_paragraph(doc: Document, text: str, style="Normal", first_line=None):
    text = normalize_spaces(text)
    if not text:
        return None
    paragraph = doc.add_paragraph(style=style)
    if first_line is not None:
        set_paragraph_indent(paragraph, first_line_chars=int(first_line * 100))
    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    add_mixed_runs(paragraph, text)
    return paragraph


def paragraph_font_spec(paragraph):
    name = paragraph.style.name if paragraph.style is not None else "Normal"
    return {
        "Thesis Abstract CN": ("楷体-简", "Times New Roman", 12),
        "Thesis Abstract EN": ("Times New Roman", "Times New Roman", 12),
        "Thesis Acknowledgement": ("宋体", "Times New Roman", 10.5),
        "Thesis Reference": ("宋体", "Times New Roman", 10.5),
        "Thesis Code": ("宋体", "Menlo", 9),
    }.get(name, ("宋体", "Times New Roman", 12))


def add_mixed_runs(paragraph, text: str):
    pattern = re.compile(r"(`[^`]+`|\[[^\]]+\]\([^)]+\))")
    pos = 0
    east, ascii_font, size = paragraph_font_spec(paragraph)
    for match in pattern.finditer(text):
        if match.start() > pos:
            run = paragraph.add_run(text[pos : match.start()])
            set_run_font(run, east, ascii_font, size)
        token = match.group(0)
        if token.startswith("`"):
            run = paragraph.add_run(token.strip("`"))
            set_run_font(run, "宋体", "Menlo", 10.5)
        else:
            label = token[1:].split("](", 1)[0]
            run = paragraph.add_run(label)
            set_run_font(run, east, ascii_font, size)
        pos = match.end()
    if pos < len(text):
        run = paragraph.add_run(text[pos:])
        set_run_font(run, east, ascii_font, size)


def add_heading(doc: Document, text: str, level: int):
    style = {1: "Thesis Heading 1", 2: "Thesis Heading 2", 3: "Thesis Heading 3"}[level]
    paragraph = doc.add_paragraph(style=style)
    paragraph.paragraph_format.keep_with_next = True
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if level == 1 else WD_ALIGN_PARAGRAPH.LEFT
    run = paragraph.add_run(text)
    set_run_font(run, "宋体", "Times New Roman", size={1: 16, 2: 14, 3: 12}[level], bold=level <= 3)
    return paragraph


def add_front_heading(doc: Document, text: str, level: int):
    style = {1: "Thesis Front Heading 1", 2: "Thesis Front Heading 2"}[level]
    paragraph = doc.add_paragraph(style=style)
    paragraph.paragraph_format.keep_with_next = True
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if level == 1 else WD_ALIGN_PARAGRAPH.LEFT
    run = paragraph.add_run(text)
    set_run_font(run, "宋体", "Times New Roman", size={1: 16, 2: 14}[level], bold=True)
    return paragraph


def add_keywords(doc: Document, label: str, text: str, english=False):
    paragraph = doc.add_paragraph(style="Thesis Keyword")
    set_paragraph_spacing(paragraph, before=12, after=0, line=1.25)
    set_paragraph_indent(paragraph, first_line_chars=0)
    run = paragraph.add_run(label)
    set_run_font(run, "宋体" if not english else "Times New Roman", "Times New Roman", 12, True)
    run = paragraph.add_run(text)
    set_run_font(run, "宋体" if not english else "Times New Roman", "Times New Roman", 12, False)


def add_cover(doc: Document):
    configure_section(doc.sections[0], header=False)
    add_center(doc, "学校代码：10022", size=14)
    for _ in range(3):
        doc.add_paragraph()
    add_center(doc, "本科毕业论文（设计）", style_name="Thesis Title CN", before=10, after=24)
    add_center(doc, TITLE_CN, style_name="Thesis Title CN", after=6)
    add_center(doc, TITLE_EN, style_name="Thesis Title EN", after=36)
    add_center(doc, AUTHOR, style_name="Thesis Cover Field", after=24)

    table = doc.add_table(rows=5, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    rows = [
        ("学    院", COLLEGE),
        ("专    业", MAJOR),
        ("班    级", CLASS_NAME),
        ("学    号", STUDENT_ID),
        ("指导教师", SUPERVISOR),
    ]
    set_table_widths(table, [2200, 5000])
    for row, (left, right) in zip(table.rows, rows):
        for idx, value in enumerate((left, right)):
            cell = row.cells[idx]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            set_paragraph_indent(p, first_line_chars=0)
            run = p.add_run(value)
            set_run_font(run, "宋体", "Times New Roman", 14)
    remove_table_borders(table)
    for _ in range(4):
        doc.add_paragraph()
    add_center(doc, DATE_TEXT, style_name="Thesis Cover Field")


def add_declarations(doc: Document):
    doc.add_section(WD_SECTION_START.NEW_PAGE)
    configure_section(doc.sections[-1], header=False)
    add_front_heading(doc, "独创性声明", 1)
    add_body_paragraph(
        doc,
        "本人声明所呈交的论文（设计）是本人在导师指导下独立进行的设计、研究工作及取得的设计、研究成果。"
        "尽我所知，除了论文（设计）中特别加以标注和致谢的地方外，论文（设计）中不包含其他人已经发表"
        "或撰写过的研究成果，本论文（设计）中没有抄袭他人研究成果和伪造数据等行为。与我共同工作的人员"
        "对本研究所做的任何贡献均已在论文（设计）中作了明确的说明并表示了谢意。",
    )
    doc.add_paragraph()
    add_body_paragraph(doc, "作者签名：                      日期：      年   月   日", first_line=0)
    doc.add_paragraph()
    add_front_heading(doc, "关于毕业论文（设计）使用授权的说明", 1)
    add_body_paragraph(
        doc,
        "本人完全了解北京林业大学有关保留、使用毕业论文（设计）的规定，即：本科生在校期间毕业论文（设计）"
        "工作的知识产权单位属北京林业大学；学校有权保留并向国家有关部门或机构送交论文（设计）的纸质版和"
        "电子版，允许毕业论文（设计）被查阅、借阅和复印；学校可以将毕业论文（设计）的全部或部分内容公开"
        "或编入有关数据库进行检索，可以允许采用影印、缩印或其它复制手段保存、汇编毕业论文（设计）。",
    )
    doc.add_paragraph()
    add_body_paragraph(doc, "作者签名：                   指导老师签名：", first_line=0)
    add_body_paragraph(doc, "日    期：      年   月   日", first_line=0)

    doc.add_section(WD_SECTION_START.NEW_PAGE)
    configure_section(doc.sections[-1], header=False)
    add_front_heading(doc, "AI工具规范使用诚信承诺书", 1)
    add_front_heading(doc, "一、AI工具使用情况说明", 2)
    add_body_paragraph(doc, "本人郑重声明，在毕业论文（设计）写作过程中使用AI工具的情况如下：")
    add_body_paragraph(doc, "□ 未使用任何AI工具（勾选此项者无需填写后续内容）", first_line=0)
    add_body_paragraph(doc, "■ 使用AI工具（勾选此项者需如实填写以下内容）", first_line=0)
    add_body_paragraph(
        doc,
        "1. 使用工具名称：ChatGPT、DeepSeek、skill-thesis-writer论文写作规范、文献数据库检索工具、"
        "LaTeX排版与图表辅助工具。",
        first_line=0,
    )
    add_body_paragraph(
        doc,
        "2. 具体用途及生成内容：用于文献检索关键词整理、论文结构草拟、学术语言润色建议、GB/T 7714-2015"
        "参考文献格式检查、LaTeX格式调整、图表生成脚本辅助编写。系统设计、实验方案、核心代码理解、"
        "数据复核、结论推导由作者结合本项目实际实现独立完成。",
        first_line=0,
    )
    add_body_paragraph(doc, "3. 生成内容占全文比例：25%。", first_line=0)
    add_front_heading(doc, "二、诚信承诺", 2)
    add_body_paragraph(
        doc,
        "本人承诺：毕业论文（设计）核心研究内容（包括实验设计、数据分析、结论推导等）均独立完成，未使用AI工具"
        "替代核心研究、实验设计、数据分析和结论形成。上述AI工具使用情况描述真实、准确、完整，无隐瞒或虚假陈述。",
    )
    doc.add_paragraph()
    add_body_paragraph(doc, "作者签名：                      日期：      年   月   日", first_line=0)


def normalize_spaces(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = text.replace(" ,", ",").replace(" .", ".")
    return text.strip()


def strip_comments(line: str) -> str:
    escaped = False
    out = []
    for ch in line:
        if ch == "%" and not escaped:
            break
        out.append(ch)
        escaped = ch == "\\" and not escaped
        if ch != "\\":
            escaped = False
    return "".join(out).rstrip()


def latex_to_text(text: str, cite_map: dict[str, int], ref_map: dict[str, str]) -> str:
    text = text.strip()
    if not text:
        return ""
    replacements = {
        r"\quad": " ",
        r"\qquad": " ",
        r"\textbackslash": "\\",
        r"\%": "%",
        r"\_": "_",
        r"\&": "&",
        r"\$": "$",
        r"\#": "#",
        r"\{": "{",
        r"\}": "}",
        r"~": " ",
        r"``": "“",
        r"''": "”",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    def cite_repl(match):
        nums = []
        for key in match.group(1).split(","):
            key = key.strip()
            if key in cite_map:
                nums.append(str(cite_map[key]))
        return "[" + ", ".join(nums) + "]" if nums else ""

    text = re.sub(r"\\cite\{([^}]+)\}", cite_repl, text)
    text = re.sub(r"\\ref\{([^}]+)\}", lambda m: ref_map.get(m.group(1), m.group(1)), text)
    text = re.sub(r"\\url\{([^}]+)\}", r"\1", text)
    for cmd in ("code", "filepath", "decision", "tightcode", "textbf", "emph", "textit", "underline"):
        text = replace_command_with_content(text, cmd)
    text = re.sub(r"\\makecell(?:\[[^\]]+\])?\{([^{}]*)\}", lambda m: m.group(1).replace("\\\\", " "), text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", "", text)
    text = text.replace("{", "").replace("}", "")
    text = text.replace("$", "")
    text = re.sub(r"_\{\\mathrm\{([^}]+)\}\}", r"_\1", text)
    text = re.sub(r"\^\{([^}]+)\}", r"^\1", text)
    text = re.sub(r"_\{([^}]+)\}", r"_\1", text)
    text = text.replace("\\\\", " ")
    return normalize_spaces(text)


def replace_command_with_content(text: str, cmd: str) -> str:
    pattern = "\\" + cmd + "{"
    while pattern in text:
        start = text.find(pattern)
        content_start = start + len(pattern)
        depth = 1
        i = content_start
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        if depth:
            break
        content = text[content_start : i - 1]
        text = text[:start] + content + text[i:]
    return text


def collect_until(lines: list[str], start: int, end_marker: str) -> tuple[str, int]:
    block = []
    i = start
    while i < len(lines):
        block.append(lines[i])
        if end_marker in lines[i]:
            break
        i += 1
    return "\n".join(block), i


def build_cite_map(tex: str) -> dict[str, int]:
    cite_map: dict[str, int] = {}
    for idx, match in enumerate(re.finditer(r"\\bibitem\{([^}]+)\}", tex), 1):
        cite_map[match.group(1)] = idx
    return cite_map


def build_reference_map(lines: list[str]) -> dict[str, str]:
    ref_map: dict[str, str] = {}
    section_no = 0
    appendix = False
    appendix_no = 0
    current_key = "0"
    fig_counts = defaultdict(int)
    tab_counts = defaultdict(int)
    i = 0
    while i < len(lines):
        line = strip_comments(lines[i])
        if r"\appendix" in line:
            appendix = True
            appendix_no = 0
            i += 1
            continue
        m_sec = re.match(r"\\section\{([^}]+)\}", line)
        if m_sec:
            if appendix:
                appendix_no += 1
                current_key = chr(ord("A") + appendix_no - 1)
            else:
                section_no += 1
                current_key = str(section_no)
            i += 1
            continue
        if r"\begin{figure}" in line:
            block, end = collect_until(lines, i, r"\end{figure}")
            label = re.search(r"\\label\{([^}]+)\}", block)
            if label:
                fig_counts[current_key] += 1
                ref_map[label.group(1)] = f"{current_key}.{fig_counts[current_key]}"
            i = end + 1
            continue
        if r"\begin{table}" in line:
            block, end = collect_until(lines, i, r"\end{table}")
            label = re.search(r"\\label\{([^}]+)\}", block)
            if label:
                tab_counts[current_key] += 1
                ref_map[label.group(1)] = f"{current_key}.{tab_counts[current_key]}"
            i = end + 1
            continue
        if r"\begin{longtable}" in line:
            block, end = collect_until(lines, i, r"\end{longtable}")
            label = re.search(r"\\label\{([^}]+)\}", block)
            if label:
                tab_counts[current_key] += 1
                ref_map[label.group(1)] = f"{current_key}.{tab_counts[current_key]}"
            i = end + 1
            continue
        i += 1
    return ref_map


def parse_bicaption(block: str, cite_map, ref_map) -> tuple[str, str]:
    match = re.search(r"\\bicaption\{(.+?)\}\{(.+?)\}", block, re.S)
    if match:
        return latex_to_text(match.group(1), cite_map, ref_map), latex_to_text(match.group(2), cite_map, ref_map)
    match = re.search(r"\\caption\{(.+?)\}", block, re.S)
    if match:
        raw = match.group(1).replace(r"\\\small", "\n")
        parts = [latex_to_text(x, cite_map, ref_map) for x in raw.split("\n") if x.strip()]
        if len(parts) > 1:
            return parts[0], parts[1]
        return parts[0] if parts else "", ""
    return "", ""


def parse_label(block: str) -> str:
    match = re.search(r"\\label\{([^}]+)\}", block)
    return match.group(1) if match else ""


def split_latex_row(row: str) -> list[str]:
    cells = []
    current = []
    depth = 0
    i = 0
    while i < len(row):
        ch = row[i]
        if ch == "{" and (i == 0 or row[i - 1] != "\\"):
            depth += 1
        elif ch == "}" and (i == 0 or row[i - 1] != "\\"):
            depth = max(0, depth - 1)
        if ch == "&" and depth == 0:
            cells.append("".join(current))
            current = []
        else:
            current.append(ch)
        i += 1
    cells.append("".join(current))
    return cells


def parse_table_rows(block: str, cite_map, ref_map) -> list[list[str]]:
    rows = []
    in_tabular = False
    for raw in block.splitlines():
        line = strip_comments(raw).strip()
        if not line:
            continue
        if r"\begin{tabular" in line or r"\begin{longtable" in line:
            in_tabular = True
            continue
        if r"\end{tabular" in line or r"\end{longtable" in line:
            break
        if not in_tabular:
            continue
        if any(token in line for token in [
            r"\toprule",
            r"\midrule",
            r"\bottomrule",
            r"\endfirsthead",
            r"\endhead",
            r"\caption",
            r"\label",
        ]):
            continue
        if line.startswith("\\") and "&" not in line:
            continue
        if line.endswith(r"\\"):
            line = line[:-2]
        if "&" not in line:
            continue
        cells = [latex_to_text(cell, cite_map, ref_map) for cell in split_latex_row(line)]
        if any(cells):
            rows.append(cells)
    return rows


def remove_table_borders(table):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = "w:" + edge
        elem = borders.find(qn(tag))
        if elem is None:
            elem = OxmlElement(tag)
            borders.append(elem)
        elem.set(qn("w:val"), "nil")


def set_three_line_borders(table):
    remove_table_borders(table)
    last_idx = len(table.rows) - 1
    for r_idx, row in enumerate(table.rows):
        tr_pr = row._tr.get_or_add_trPr()
        cant_split = tr_pr.find(qn("w:cantSplit"))
        if cant_split is None:
            tr_pr.append(OxmlElement("w:cantSplit"))
        for cell in row.cells:
            clear_cell_borders(cell)
            if r_idx == 0:
                set_cell_border(cell, "top", size=12)
                set_cell_border(cell, "bottom", size=8)
            if r_idx == last_idx:
                set_cell_border(cell, "bottom", size=12)
    if table.rows:
        tr_pr = table.rows[0]._tr.get_or_add_trPr()
        header = OxmlElement("w:tblHeader")
        header.set(qn("w:val"), "true")
        tr_pr.append(header)


def clear_cell_borders(cell):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        elem = borders.find(qn("w:" + edge))
        if elem is None:
            elem = OxmlElement("w:" + edge)
            borders.append(elem)
        elem.set(qn("w:val"), "nil")


def set_cell_border(cell, edge: str, *, size=8):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    elem = borders.find(qn("w:" + edge))
    if elem is None:
        elem = OxmlElement("w:" + edge)
        borders.append(elem)
    elem.set(qn("w:val"), "single")
    elem.set(qn("w:sz"), str(size))
    elem.set(qn("w:color"), "000000")


def set_cell_margins(cell, top=80, start=100, bottom=80, end=100):
    tc_pr = cell._tc.get_or_add_tcPr()
    mar = tc_pr.find(qn("w:tcMar"))
    if mar is None:
        mar = OxmlElement("w:tcMar")
        tc_pr.append(mar)
    for edge, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = mar.find(qn("w:" + edge))
        if node is None:
            node = OxmlElement("w:" + edge)
            mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_widths(table, widths: list[int]):
    table.autofit = False
    tbl = table._tbl
    tbl_grid = tbl.tblGrid
    if tbl_grid is None:
        tbl_grid = OxmlElement("w:tblGrid")
        tbl.insert(0, tbl_grid)
    for child in list(tbl_grid):
        tbl_grid.remove(child)
    for width in widths:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        tbl_grid.append(col)
    for row in table.rows:
        for idx, cell in enumerate(row.cells):
            width = widths[min(idx, len(widths) - 1)]
            cell.width = Inches(width / 1440)
            tc_pr = cell._tc.get_or_add_tcPr()
            tcw = tc_pr.find(qn("w:tcW"))
            if tcw is None:
                tcw = OxmlElement("w:tcW")
                tc_pr.append(tcw)
            tcw.set(qn("w:w"), str(width))
            tcw.set(qn("w:type"), "dxa")


def add_table(doc: Document, rows: list[list[str]], caption_cn: str, caption_en: str, number: str):
    if not rows:
        return
    if caption_cn:
        cap = doc.add_paragraph(style="Thesis Caption")
        cap.paragraph_format.keep_with_next = True
        run = cap.add_run(f"表{number} {caption_cn}")
        set_run_font(run, "宋体", "Times New Roman", 9, True)
        if caption_en:
            cap2 = doc.add_paragraph(style="Thesis Caption")
            cap2.paragraph_format.keep_with_next = True
            run = cap2.add_run(f"Table {number} {caption_en}")
            set_run_font(run, "宋体", "Times New Roman", 9, True)
    cols = max(len(row) for row in rows)
    table = doc.add_table(rows=len(rows), cols=cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    widths = compute_widths(rows, cols)
    set_table_widths(table, widths)
    set_three_line_borders(table)
    for r_idx, row in enumerate(rows):
        for c_idx in range(cols):
            cell = table.rows[r_idx].cells[c_idx]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)
            p = cell.paragraphs[0]
            p.style = doc.styles["Thesis Table"]
            set_paragraph_indent(p, first_line_chars=0)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if r_idx == 0 or short_cell(row[c_idx] if c_idx < len(row) else "") else WD_ALIGN_PARAGRAPH.LEFT
            text = row[c_idx] if c_idx < len(row) else ""
            text = add_wrap_opportunities(text)
            run = p.add_run(text)
            set_run_font(run, "宋体", "Times New Roman", 9, r_idx == 0)
    doc.add_paragraph()


def short_cell(text: str) -> bool:
    return len(text) <= 18 and "\n" not in text


def add_wrap_opportunities(text: str) -> str:
    if len(text) < 24:
        return text
    # Word can miss wrap points in paths, code-like identifiers, and URLs.
    # Zero-width spaces keep the visible text unchanged while allowing wrapping.
    return re.sub(r"([/_\-.])", lambda match: match.group(1) + "\u200b", text)


def compute_widths(rows: list[list[str]], cols: int) -> list[int]:
    scores = []
    for idx in range(cols):
        max_len = max((len(row[idx]) if idx < len(row) else 0) for row in rows)
        scores.append(max(10, min(max_len, 60)))
    total_score = sum(scores) or 1
    widths = [max(900, int(PAGE_WIDTH_DXA * score / total_score)) for score in scores]
    diff = PAGE_WIDTH_DXA - sum(widths)
    widths[-1] += diff
    return widths


def load_font(size=28, bold=False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Songti.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                pass
    return ImageFont.load_default()


def wrap_text(draw, text: str, font, width: int) -> list[str]:
    if not text:
        return [""]
    lines = []
    current = ""
    for ch in text:
        test = current + ch
        if draw.textbbox((0, 0), test, font=font)[2] <= width or not current:
            current = test
        else:
            lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines


def draw_centered_text(draw, box, text, font, fill=(30, 41, 59)):
    x1, y1, x2, y2 = box
    lines = wrap_text(draw, text, font, x2 - x1 - 24)
    line_h = font.size + 5 if hasattr(font, "size") else 18
    total_h = line_h * len(lines)
    y = y1 + (y2 - y1 - total_h) / 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = x1 + (x2 - x1 - (bbox[2] - bbox[0])) / 2
        draw.text((x, y), line, font=font, fill=fill)
        y += line_h


def draw_arrow(draw, start, end, fill=(51, 65, 85)):
    draw.line([start, end], fill=fill, width=4)
    x1, y1 = start
    x2, y2 = end
    if x2 >= x1:
        pts = [(x2, y2), (x2 - 14, y2 - 9), (x2 - 14, y2 + 9)]
    else:
        pts = [(x2, y2), (x2 + 14, y2 - 9), (x2 + 14, y2 + 9)]
    draw.polygon(pts, fill=fill)


def generate_figure(label: str, caption: str) -> Path:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURE_DIR / f"{label.replace(':', '_') or 'figure'}.png"
    if path.exists():
        return path
    w, h = 1600, 850
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)
    title_font = load_font(34, True)
    box_font = load_font(24)
    small_font = load_font(20)
    draw.text((60, 36), caption[:70], font=title_font, fill=(15, 23, 42))

    palette = [(221, 238, 255), (221, 243, 226), (252, 239, 203), (250, 217, 216), (236, 228, 250)]
    if label == "fig:redteam":
        cats = [
            ("Prompt Injection", 15),
            ("Jailbreak", 16),
            ("PII/Sensitive", 14),
            ("Obfuscation", 13),
            ("Multi-Language", 12),
            ("Tool Abuse", 10),
            ("Social Engineering", 10),
            ("Data Exfiltration", 10),
            ("RAG Poisoning", 8),
            ("Confused Deputy", 7),
        ]
        max_v = max(v for _, v in cats)
        x0, y0 = 420, 135
        for idx, (name, value) in enumerate(cats):
            y = y0 + idx * 58
            draw.text((80, y + 6), name, font=small_font, fill=(30, 41, 59))
            bar_w = int(850 * value / max_v)
            draw.rounded_rectangle((x0, y, x0 + bar_w, y + 34), radius=8, fill=(207, 228, 255), outline=(51, 65, 85), width=2)
            draw.text((x0 + bar_w + 16, y + 3), str(value), font=small_font, fill=(30, 41, 59))
    elif label in {"fig:risk", "fig:benchmark-compare", "fig:latency"}:
        data = {
            "fig:risk": [("Intent", 5), ("Rules", 4), ("Scanners", 4), ("PII", 3), ("Secrets", 3), ("Boost", 2)],
            "fig:benchmark-compare": [("轻量规则", 4), ("完整扫描器", 7)],
            "fig:latency": [("parse", 1), ("intent", 1), ("rules", 1), ("scanners", 4), ("decision", 1)],
        }[label]
        max_v = max(v for _, v in data)
        base_y = 710
        x0 = 140
        gap = 120 if len(data) > 3 else 260
        for idx, (name, value) in enumerate(data):
            x = x0 + idx * gap
            bar_h = int(470 * value / max_v)
            draw.rounded_rectangle((x, base_y - bar_h, x + 70, base_y), radius=8, fill=(207, 228, 255), outline=(51, 65, 85), width=2)
            draw.text((x + 20, base_y - bar_h - 35), str(value), font=small_font, fill=(30, 41, 59))
            draw.text((x - 18, base_y + 18), name, font=small_font, fill=(30, 41, 59))
        draw.line((90, base_y, 1500, base_y), fill=(148, 163, 184), width=2)
    else:
        flow_defs = {
            "fig:trust-boundaries": ["外部消息", "安全壳入口", "Proxy扫描", "Agent门控", "OpenClaw/MCP"],
            "fig:architecture": ["消息入口", "Agent Runtime", "Proxy Service", "OpenClaw/MCP", "Trace/Audit"],
            "fig:proxy-pipeline": ["parse", "intent", "rules", "scanners", "decision", "audit"],
            "fig:agent-pipeline": ["input", "policy", "pre-tool", "executor", "post-tool", "response"],
            "fig:intervention-flow": ["暂停触发", "创建审批项", "控制台审核", "审批后重放", "完成回复"],
            "fig:delegation": ["Main Agent", "Gate", "Subagent/Tool", "Trace"],
            "fig:trace-evidence": ["输入扫描", "工具计划", "Pre gate", "Tool exec", "Post gate"],
        }
        labels = flow_defs.get(label, ["输入", "扫描", "门控", "执行", "审计"])
        n = len(labels)
        bw = 230 if n <= 5 else 190
        bh = 120
        gap = (w - 160 - n * bw) // max(1, n - 1)
        y = 300
        boxes = []
        for idx, text in enumerate(labels):
            x = 80 + idx * (bw + gap)
            box = (x, y, x + bw, y + bh)
            boxes.append(box)
            draw.rounded_rectangle(box, radius=18, fill=palette[idx % len(palette)], outline=(51, 65, 85), width=3)
            draw_centered_text(draw, box, text, box_font)
        for left, right in zip(boxes, boxes[1:]):
            draw_arrow(draw, (left[2] + 6, y + bh // 2), (right[0] - 6, y + bh // 2))
        note = "关键边界均由后端策略层判定，并写入 Trace/Audit 证据链"
        draw.rounded_rectangle((250, 585, 1350, 690), radius=18, fill=(238, 242, 246), outline=(148, 163, 184), width=2)
        draw_centered_text(draw, (250, 585, 1350, 690), note, small_font)
    img.save(path)
    return path


def parse_includegraphics(block: str) -> tuple[str, str]:
    match = re.search(r"\\includegraphics(?:\[(?P<options>[^\]]*)\])?\{(?P<path>[^}]+)\}", block, re.S)
    if not match:
        return "", ""
    return match.group("path"), match.group("options") or ""


def parse_graphic_scale(options: str) -> float:
    match = re.search(r"width\s*=\s*(?P<scale>(?:\d+(?:\.\d*)?|\.\d+)?)\\textwidth", options)
    if not match:
        return 1.0
    scale = match.group("scale")
    if not scale:
        return 1.0
    return max(0.35, min(1.0, float(scale)))


def resolve_latex_graphic(path_text: str) -> Path:
    raw = Path(path_text)
    candidates: list[Path] = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.append(LATEX_DIR / raw)
        candidates.extend(base / raw for base in GRAPHIC_SEARCH_DIRS)

    expanded: list[Path] = []
    for candidate in candidates:
        if candidate.suffix:
            expanded.append(candidate)
        else:
            expanded.extend(candidate.with_suffix(ext) for ext in (".pdf", ".png", ".jpg", ".jpeg"))
    for candidate in expanded:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"cannot resolve LaTeX graphic: {path_text}")


def convert_pdf_to_png(pdf_path: Path) -> Path:
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise RuntimeError("pdftoppm is required to convert LaTeX PDF figures for DOCX output")
    LATEX_FIGURE_RENDER_DIR.mkdir(parents=True, exist_ok=True)
    try:
        relative = pdf_path.relative_to(LATEX_DIR)
    except ValueError:
        relative = pdf_path
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(relative.with_suffix("")))
    prefix = LATEX_FIGURE_RENDER_DIR / safe_stem
    out_path = Path(str(prefix) + ".png")
    if out_path.exists() and out_path.stat().st_mtime >= pdf_path.stat().st_mtime:
        return out_path
    subprocess.run(
        [pdftoppm, "-singlefile", "-png", "-r", "220", str(pdf_path), str(prefix)],
        check=True,
        cwd=str(DOCX_DIR),
    )
    if not out_path.exists():
        raise RuntimeError(f"pdftoppm did not produce expected PNG: {out_path}")
    return out_path


def prepare_latex_graphic(path_text: str) -> Path:
    graphic = resolve_latex_graphic(path_text)
    if graphic.suffix.lower() == ".pdf":
        return convert_pdf_to_png(graphic)
    if graphic.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        return graphic
    raise RuntimeError(f"unsupported LaTeX graphic format for DOCX output: {graphic}")


def add_figure(
    doc: Document,
    caption_cn: str,
    caption_en: str,
    number: str,
    label: str,
    image_path: Path,
    scale: float = 1.0,
):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    run.add_picture(str(image_path), width=Cm(14.6 * scale))
    cap = doc.add_paragraph(style="Thesis Caption")
    cap.paragraph_format.keep_with_next = True
    run = cap.add_run(f"图{number} {caption_cn}")
    set_run_font(run, "宋体", "Times New Roman", 9, True)
    if caption_en:
        cap2 = doc.add_paragraph(style="Thesis Caption")
        cap2.paragraph_format.keep_with_next = True
        run = cap2.add_run(f"Figure {number} {caption_en}")
        set_run_font(run, "宋体", "Times New Roman", 9, True)
    doc.add_paragraph()


class ThesisBuilder:
    def __init__(self, doc: Document, tex: str):
        self.doc = doc
        self.tex = tex
        self.cite_map = build_cite_map(tex)
        start = tex.index(r"\section*{摘要}")
        self.lines = tex[start:].splitlines()
        self.ref_map = build_reference_map(self.lines)
        self.section_no = 0
        self.sub_no = 0
        self.subsub_no = 0
        self.appendix = False
        self.appendix_no = 0
        self.current_key = "0"
        self.fig_counts = defaultdict(int)
        self.tab_counts = defaultdict(int)
        self.body_started = False
        self.in_bibliography = False
        self.reference_count = 0
        self.pending: list[str] = []
        self.current_style = "Normal"
        self.pending_break = False

    def clean(self, text: str) -> str:
        return latex_to_text(text, self.cite_map, self.ref_map)

    def flush(self, style=None):
        if not self.pending:
            return
        style = style or self.current_style
        text = " ".join(x.strip() for x in self.pending if x.strip())
        self.pending = []
        cleaned = self.clean(text)
        if cleaned:
            add_body_paragraph(self.doc, cleaned, style=style)

    def add_section_heading(self, title: str, level: int, starred=False):
        self.flush()
        title = self.clean(title)
        if starred:
            if self.pending_break:
                add_page_break(self.doc)
                self.pending_break = False
            if title == "主要符号与缩略词对照表":
                paragraph = add_body_paragraph(self.doc, title, style="Normal")
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                set_paragraph_outline_level(paragraph, 0)
                self.current_style = "Normal"
                return
            add_heading(self.doc, title, 1)
            if title == "摘要":
                self.current_style = "Thesis Abstract CN"
            elif title == "Abstract":
                self.current_style = "Thesis Abstract EN"
            elif title == "致谢":
                self.current_style = "Thesis Acknowledgement"
            else:
                self.current_style = "Normal"
            return
        if level == 1:
            if self.appendix:
                self.appendix_no += 1
                self.current_key = chr(ord("A") + self.appendix_no - 1)
                heading = f"附录{self.current_key}  {title}"
            else:
                self.section_no += 1
                self.current_key = str(self.section_no)
                heading = f"{self.section_no} {title}"
            self.sub_no = 0
            self.subsub_no = 0
            if self.pending_break:
                add_page_break(self.doc)
                self.pending_break = False
            elif self.body_started:
                add_page_break(self.doc)
            self.body_started = True
            self.current_style = "Normal"
            add_heading(self.doc, heading, 1)
        elif level == 2:
            self.sub_no += 1
            self.subsub_no = 0
            prefix = f"{self.current_key}.{self.sub_no}"
            add_heading(self.doc, f"{prefix} {title}", 2)
        elif level == 3:
            self.subsub_no += 1
            prefix = f"{self.current_key}.{self.sub_no}.{self.subsub_no}"
            add_heading(self.doc, f"{prefix} {title}", 3)

    def add_table_block(self, block: str):
        self.flush()
        cn, en = parse_bicaption(block, self.cite_map, self.ref_map)
        label = parse_label(block)
        self.tab_counts[self.current_key] += 1
        number = self.ref_map.get(label, f"{self.current_key}.{self.tab_counts[self.current_key]}")
        rows = parse_table_rows(block, self.cite_map, self.ref_map)
        add_table(self.doc, rows, cn, en, number)

    def add_longtable_block(self, block: str):
        self.flush()
        cn, en = parse_bicaption(block, self.cite_map, self.ref_map)
        label = parse_label(block)
        if not cn and "符号或缩略词" in block:
            cn, en = "主要符号与缩略词对照表", "List of symbols and abbreviations"
        self.tab_counts[self.current_key] += 1
        number = self.ref_map.get(label, f"{self.current_key}.{self.tab_counts[self.current_key]}")
        rows = parse_table_rows(block, self.cite_map, self.ref_map)
        if cn == "主要符号与缩略词对照表":
            # The abbreviation list is a required front-matter table, not a numbered body table.
            add_table(self.doc, rows, "", "", number)
        else:
            add_table(self.doc, rows, cn, en, number)

    def add_figure_block(self, block: str):
        self.flush()
        cn, en = parse_bicaption(block, self.cite_map, self.ref_map)
        label = parse_label(block)
        graphic_path, graphic_options = parse_includegraphics(block)
        image_path = prepare_latex_graphic(graphic_path)
        scale = parse_graphic_scale(graphic_options)
        self.fig_counts[self.current_key] += 1
        number = self.ref_map.get(label, f"{self.current_key}.{self.fig_counts[self.current_key]}")
        add_figure(self.doc, cn, en, number, label, image_path, scale)

    def add_code_block(self, code: str):
        self.flush()
        for line in code.strip("\n").splitlines():
            paragraph = self.doc.add_paragraph(style="Thesis Code")
            set_paragraph_indent(paragraph, first_line_chars=0)
            run = paragraph.add_run(line.lstrip())
            set_run_font(run, "宋体", "Menlo", 9)

    def add_equation_block(self, block: str):
        self.flush()
        equation = self.clean(block.replace(r"\begin{equation}", "").replace(r"\end{equation}", ""))
        paragraph = self.doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_paragraph_indent(paragraph, first_line_chars=0)
        run = paragraph.add_run(equation)
        set_run_font(run, "宋体", "Times New Roman", 12)

    def add_toc(self):
        self.flush()
        add_page_break(self.doc)
        self.pending_break = False
        add_front_heading(self.doc, "目  录", 1)
        paragraph = self.doc.add_paragraph(style="Thesis TOC")
        set_paragraph_indent(paragraph, first_line_chars=0)
        add_field(paragraph, r'TOC \o "1-3" \h \z \u')
        add_page_break(self.doc)

    def add_bibliography_heading(self):
        self.flush()
        if self.pending_break:
            add_page_break(self.doc)
            self.pending_break = False
        else:
            add_page_break(self.doc)
        add_heading(self.doc, "参考文献", 1)
        self.in_bibliography = True
        self.reference_count = 0
        self.current_style = "Thesis Reference"

    def process_bibitem(self, line: str):
        match = re.match(r"\\bibitem\{([^}]+)\}\s*(.*)", line)
        if not match:
            return
        self.reference_count += 1
        text = self.clean(match.group(2))
        paragraph = self.doc.add_paragraph(style="Thesis Reference")
        set_paragraph_indent(paragraph, left_chars=202, hanging_chars=202)
        run = paragraph.add_run(f"[{self.reference_count}] {text}")
        set_run_font(run, "宋体", "Times New Roman", 10.5)

    def parse(self):
        i = 0
        while i < len(self.lines):
            line = strip_comments(self.lines[i]).strip()
            if not line:
                self.flush()
                i += 1
                continue
            if line == r"\end{document}":
                self.flush()
                break
            if line in {r"\begin{cnabstract}", r"\end{cnabstract}", r"\begin{enabstract}", r"\end{enabstract}"}:
                i += 1
                continue
            if r"\appendix" in line:
                self.flush()
                self.appendix = True
                i += 1
                continue
            if r"\pagenumbering{arabic}" in line:
                self.flush()
                self.doc.add_section(WD_SECTION_START.NEW_PAGE)
                configure_section(self.doc.sections[-1], page_fmt="decimal", start=1, header=True)
                self.pending_break = False
                i += 1
                continue
            if r"\tableofcontents" in line:
                self.add_toc()
                i += 1
                continue
            if r"\begin{thebibliography}" in line:
                self.add_bibliography_heading()
                i += 1
                continue
            if r"\end{thebibliography}" in line:
                self.in_bibliography = False
                i += 1
                continue
            if self.in_bibliography:
                if line.startswith(r"\bibitem"):
                    self.process_bibitem(line)
                i += 1
                continue
            if r"\begin{figure}" in line:
                block, end = collect_until(self.lines, i, r"\end{figure}")
                self.add_figure_block(block)
                i = end + 1
                continue
            if r"\begin{table}" in line:
                block, end = collect_until(self.lines, i, r"\end{table}")
                self.add_table_block(block)
                i = end + 1
                continue
            if r"\begin{longtable}" in line:
                block, end = collect_until(self.lines, i, r"\end{longtable}")
                self.add_longtable_block(block)
                i = end + 1
                continue
            if r"\begin{lstlisting}" in line:
                block, end = collect_until(self.lines, i + 1, r"\end{lstlisting}")
                code = block.replace(r"\end{lstlisting}", "")
                self.add_code_block(code)
                i = end + 1
                continue
            if r"\begin{equation}" in line:
                block, end = collect_until(self.lines, i, r"\end{equation}")
                self.add_equation_block(block)
                i = end + 1
                continue
            if line.startswith(r"\begin{enumerate}"):
                i = self.process_enumerate(i + 1)
                continue
            if line.startswith(r"\clearpage"):
                self.flush()
                self.pending_break = True
                i += 1
                continue
            if line.startswith((r"\addcontentsline", r"\setcounter", r"\thispagestyle", r"\vspace", r"\small", r"\footnotesize", r"\normalsize", r"\setlength")):
                i += 1
                continue
            m = re.match(r"\\section\*\{(.+)\}", line)
            if m:
                self.add_section_heading(m.group(1), 1, starred=True)
                i += 1
                continue
            m = re.match(r"\\section\{(.+)\}", line)
            if m:
                self.add_section_heading(m.group(1), 1)
                i += 1
                continue
            m = re.match(r"\\subsection\*\{(.+)\}", line)
            if m:
                self.add_section_heading(m.group(1), 2, starred=True)
                i += 1
                continue
            m = re.match(r"\\subsection\{(.+)\}", line)
            if m:
                self.add_section_heading(m.group(1), 2)
                i += 1
                continue
            m = re.match(r"\\subsubsection\{(.+)\}", line)
            if m:
                self.add_section_heading(m.group(1), 3)
                i += 1
                continue
            if r"\textbf{关键词" in line or r"\textbf{Keywords" in line:
                self.flush()
                cleaned = self.clean(line.replace(r"\noindent", "").replace(r"\keywordspace", ""))
                if cleaned.startswith("关键词："):
                    add_keywords(self.doc, "关键词：", cleaned.replace("关键词：", "", 1), english=False)
                elif cleaned.startswith("Keywords:"):
                    add_keywords(self.doc, "Keywords:", cleaned.replace("Keywords:", "", 1), english=True)
                i += 1
                continue
            line = re.sub(r"^\\noindent\s*", "", line)
            self.pending.append(line)
            i += 1
        self.flush()

    def process_enumerate(self, i: int) -> int:
        self.flush()
        item_lines: list[str] = []
        counter = 0
        while i < len(self.lines):
            line = strip_comments(self.lines[i]).strip()
            if line.startswith(r"\end{enumerate}"):
                if item_lines:
                    counter += 1
                    self.add_numbered_item(counter, " ".join(item_lines))
                return i + 1
            if line.startswith(r"\item"):
                if item_lines:
                    counter += 1
                    self.add_numbered_item(counter, " ".join(item_lines))
                    item_lines = []
                item_lines.append(line.replace(r"\item", "", 1).strip())
            elif line:
                item_lines.append(line)
            i += 1
        return i

    def add_numbered_item(self, number: int, text: str):
        cleaned = self.clean(text)
        add_body_paragraph(self.doc, f"（{number}）{cleaned}", style="Normal")


def update_settings_for_fields(docx_path: Path):
    tmp_path = docx_path.with_suffix(".tmp.docx")
    with zipfile.ZipFile(docx_path, "r") as src, zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "word/settings.xml":
                text = data.decode("utf-8")
                if "w:updateFields" not in text:
                    text = text.replace("</w:settings>", '<w:updateFields w:val="true"/></w:settings>')
                data = text.encode("utf-8")
            dst.writestr(item, data)
    tmp_path.replace(docx_path)


def patch_detector_ooxml(docx_path: Path):
    tmp_path = docx_path.with_suffix(".detector.tmp.docx")
    with zipfile.ZipFile(docx_path, "r") as src, zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "word/styles.xml":
                data = patch_styles_xml(data)
            dst.writestr(item, data)
    tmp_path.replace(docx_path)


def patch_styles_xml(data: bytes) -> bytes:
    from lxml import etree

    root = etree.fromstring(data)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    normal_ids = root.xpath("./w:style[w:name/@w:val='Normal']/@w:styleId", namespaces=ns)
    normal_id = normal_ids[0] if normal_ids else "Normal"

    for style_id, display_name, left_chars, bold in [
        ("TOC1", "toc 1", 0, True),
        ("TOC2", "toc 2", 100, False),
        ("TOC3", "toc 3", 100, False),
    ]:
        configure_raw_toc_style(root, style_id, display_name, normal_id, left_chars, bold)
    return etree.tostring(root, encoding="utf-8", xml_declaration=True, standalone=True)


def configure_raw_toc_style(root, style_id: str, display_name: str, normal_id: str, left_chars: int, bold: bool):
    from lxml import etree

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    matches = root.xpath(f"./w:style[@w:styleId='{style_id}']", namespaces=ns)
    if matches:
        style = matches[0]
        for child in list(style):
            style.remove(child)
    else:
        style = etree.Element(qn("w:style"))
        style.set(qn("w:type"), "paragraph")
        style.set(qn("w:styleId"), style_id)
        root.append(style)

    name = etree.SubElement(style, qn("w:name"))
    name.set(qn("w:val"), display_name)
    based_on = etree.SubElement(style, qn("w:basedOn"))
    based_on.set(qn("w:val"), normal_id)
    next_style = etree.SubElement(style, qn("w:next"))
    next_style.set(qn("w:val"), normal_id)
    ui_priority = etree.SubElement(style, qn("w:uiPriority"))
    ui_priority.set(qn("w:val"), "39")
    etree.SubElement(style, qn("w:unhideWhenUsed"))

    ppr = etree.SubElement(style, qn("w:pPr"))
    spacing = etree.SubElement(ppr, qn("w:spacing"))
    spacing.set(qn("w:after"), "0")
    spacing.set(qn("w:line"), "300")
    spacing.set(qn("w:lineRule"), "auto")
    ind = etree.SubElement(ppr, qn("w:ind"))
    ind.set(qn("w:firstLineChars"), "0")
    ind.set(qn("w:firstLine"), "0")
    ind.set(qn("w:leftChars"), str(left_chars))
    ind.set(qn("w:left"), str(left_chars))

    rpr = etree.SubElement(style, qn("w:rPr"))
    fonts = etree.SubElement(rpr, qn("w:rFonts"))
    fonts.set(qn("w:ascii"), "Times New Roman")
    fonts.set(qn("w:eastAsia"), "宋体")
    fonts.set(qn("w:hAnsi"), "Times New Roman")
    if bold:
        etree.SubElement(rpr, qn("w:b"))
        etree.SubElement(rpr, qn("w:bCs"))
    size = etree.SubElement(rpr, qn("w:sz"))
    size.set(qn("w:val"), "21")


def generate_publication_figures():
    if not FIGURE_SCRIPT.exists():
        return
    python = THESIS_VENV_PYTHON if THESIS_VENV_PYTHON.exists() else Path(sys.executable)
    subprocess.run([str(python), str(FIGURE_SCRIPT)], check=True, cwd=str(ROOT.parent))


def refresh_docx_with_libreoffice(docx_path: Path) -> bool:
    soffice = shutil.which("soffice") or "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    if not Path(soffice).exists():
        return False
    refresh_dir = DOCX_DIR / "lo_refresh"
    refresh_dir.mkdir(parents=True, exist_ok=True)
    for old in refresh_dir.glob("*"):
        old.unlink()
    profile = DOCX_DIR / ".lo_profile_refresh"
    profile.mkdir(exist_ok=True)
    cmd = [
        soffice,
        "--headless",
        f"-env:UserInstallation=file://{profile}",
        "--convert-to",
        "docx",
        "--outdir",
        str(refresh_dir),
        str(docx_path),
    ]
    proc = subprocess.run(cmd, text=True, capture_output=True, cwd=str(DOCX_DIR))
    refreshed = refresh_dir / docx_path.name
    if proc.returncode == 0 and refreshed.exists() and refreshed.stat().st_size > 0:
        refreshed.replace(docx_path)
        return True
    return False


def audit_docx(docx_path: Path):
    required = [
        "摘要",
        "Abstract",
        "目  录",
        "主要符号与缩略词对照表",
        "1 绪论",
        "参考文献",
        "致谢",
        "附录A",
        "班    级",
        "230206108",
        "生成内容占全文比例：25%。",
        "Agent-Firewall定位为OpenClaw外侧的安全壳",
        "关键词：智能体安全，工具调用，提示词注入，RBAC，OpenClaw",
        "图3.1 Agent-Firewall总体架构",
        "表5.2 本机工具流与运行时合同联调结果",
    ]
    with zipfile.ZipFile(docx_path) as zf:
        document_xml = zf.read("word/document.xml").decode("utf-8")
        styles_xml = zf.read("word/styles.xml").decode("utf-8")
        header_xml = "\n".join(
            zf.read(name).decode("utf-8")
            for name in zf.namelist()
            if name.startswith("word/header") and name.endswith(".xml")
        )
    from lxml import etree

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    root = etree.fromstring(document_xml.encode("utf-8"))
    paragraphs = ["".join(p.xpath(".//w:t/text()", namespaces=ns)) for p in root.xpath(".//w:p", namespaces=ns)]
    plain_text = "\n".join(paragraphs).replace("\u200b", "")
    missing = [text for text in required if text not in plain_text]
    if missing:
        raise RuntimeError(f"missing required DOCX text: {missing}")
    if "请在 Word" in plain_text or "请更新目录" in plain_text:
        raise RuntimeError("TOC placeholder text remains in DOCX")
    for token in ["w:pgMar", "w:headerReference", "w:footerReference", "w:tblGrid"]:
        if token not in document_xml and token not in styles_xml:
            raise RuntimeError(f"missing required OOXML token: {token}")
    required_style_tokens = [
        'w:firstLineChars="200"',
        'w:styleId="TOC1"',
        'w:styleId="TOC2"',
        'w:styleId="TOC3"',
        'w:leftChars="100"',
        'w:leftChars="202"',
        'w:hangingChars="202"',
    ]
    for token in required_style_tokens:
        if token not in styles_xml:
            raise RuntimeError(f"missing detector-oriented style token: {token}")
    if "楷体-简" not in styles_xml and "STKaitiSC-Regular" not in styles_xml and "Kaiti SC" not in styles_xml:
        raise RuntimeError("Chinese abstract style is not configured to a Simplified Chinese Kaiti font")
    if 'w:bottom w:val="single"' not in header_xml and 'w:bottom w:sz=' not in header_xml:
        raise RuntimeError("header bottom border is missing")
    if re.search(r"[图表]\d+(?:\.\d+)?  [^\n]+", plain_text):
        raise RuntimeError("caption still contains two spaces between number and title")
    if "..." in plain_text:
        raise RuntimeError("half-width ellipsis remains in DOCX text")
    if not root.xpath(".//w:tcBorders/w:top[@w:val='single']", namespaces=ns):
        raise RuntimeError("table cell-level top borders are missing")


def build():
    DOCX_DIR.mkdir(parents=True, exist_ok=True)
    tex = TEX_PATH.read_text(encoding="utf-8")
    doc = Document()
    configure_styles(doc)
    add_cover(doc)
    add_declarations(doc)

    doc.add_section(WD_SECTION_START.NEW_PAGE)
    configure_section(doc.sections[-1], page_fmt="upperRoman", start=1, header=True)
    builder = ThesisBuilder(doc, tex)
    builder.parse()
    doc.core_properties.title = TITLE_CN
    doc.core_properties.author = AUTHOR
    doc.core_properties.subject = "北京林业大学本科毕业论文（设计）"
    doc.save(OUT_PATH)
    update_settings_for_fields(OUT_PATH)
    patch_detector_ooxml(OUT_PATH)
    audit_docx(OUT_PATH)
    print(OUT_PATH)


if __name__ == "__main__":
    build()
