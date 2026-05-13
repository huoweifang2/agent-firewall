#!/usr/bin/env python3
"""Rebuild the BFU thesis DOCX from article.md without rewriting content."""

from __future__ import annotations

import re
import shutil
import sys
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.shared import Cm, Pt
from PIL import Image

HERE = Path(__file__).resolve().parent
ARTICLE_DIR = HERE.parent
ARTICLE_PATH = ARTICLE_DIR / "article.md"
TARGET_PATH = HERE / "霍玮放-本科毕业论文（设计）.docx"
BACKUP_GLOB = "霍玮放-本科毕业论文（设计）.backup-*.docx"

sys.path.insert(0, str(HERE))
import build_thesis_docx as thesis  # noqa: E402


@dataclass
class Block:
    kind: str
    text: str = ""
    level: int = 0
    path: str = ""
    rows: list[list[str]] | None = None


def backup_target() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = TARGET_PATH.with_name(f"{TARGET_PATH.stem}.backup-{timestamp}.docx")
    if TARGET_PATH.exists():
        shutil.copy2(TARGET_PATH, backup)
    return backup


def find_line(lines: list[str], value: str) -> int:
    for index, line in enumerate(lines):
        if line.strip() == value:
            return index
    raise RuntimeError(f"missing markdown section: {value}")


def find_first(lines: list[str], pattern: str) -> int:
    regex = re.compile(pattern)
    for index, line in enumerate(lines):
        if regex.match(line.strip()):
            return index
    raise RuntimeError(f"missing markdown section pattern: {pattern}")


def clean_inline(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.strip()


def parse_keyword(line: str, label: str) -> str:
    pattern = r"^\*\*" + re.escape(label) + r"[:：]\*\*\s*(.*)$"
    match = re.match(pattern, line.strip())
    if not match:
        raise RuntimeError(f"cannot parse keyword line: {line}")
    return match.group(1).strip()


def parse_markdown_table(lines: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [clean_inline(cell) for cell in stripped.strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells):
            continue
        rows.append(cells)
    return rows


def is_block_start(line: str) -> bool:
    stripped = line.strip()
    return (
        not stripped
        or stripped.startswith("#")
        or stripped.startswith("```")
        or stripped.startswith("|")
        or re.match(r"^!\[[^\]]+\]\([^)]+\)$", stripped) is not None
    )


def parse_blocks(lines: list[str]) -> list[Block]:
    blocks: list[Block] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        if stripped.startswith("```"):
            code: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            blocks.append(Block(kind="code", text="\n".join(code)))
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            blocks.append(Block(kind="heading", level=len(heading.group(1)), text=heading.group(2).strip()))
            i += 1
            continue

        image = re.match(r"^!\[([^\]]+)\]\(([^)]+)\)$", stripped)
        if image:
            caption = image.group(1).strip()
            blocks.append(Block(kind="image", text=caption, path=image.group(2).strip()))
            i += 1
            j = i
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].strip() == caption:
                i = j + 1
            continue

        if stripped.startswith("|"):
            table_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            blocks.append(Block(kind="table", rows=parse_markdown_table(table_lines)))
            continue

        parts: list[str] = []
        while i < len(lines) and not is_block_start(lines[i]):
            parts.append(lines[i].strip())
            i += 1
        blocks.append(Block(kind="paragraph", text=" ".join(parts).strip()))

    return blocks


def split_article(md: str) -> dict[str, object]:
    lines = md.splitlines()
    title = lines[0].removeprefix("#").strip()
    cn_start = find_line(lines, "## 摘要") + 1
    en_start = find_line(lines, "## Abstract") + 1
    symbols_start = find_line(lines, "## 主要符号与缩略词") + 1
    body_start = find_first(lines, r"^#\s+1\s+")

    cn_lines = lines[cn_start : en_start - 1]
    en_lines = lines[en_start : symbols_start - 1]
    symbols_lines = lines[symbols_start:body_start]
    body_lines = lines[body_start:]

    cn_keywords = ""
    en_keywords = ""
    cn_text_lines: list[str] = []
    en_text_lines: list[str] = []

    for line in cn_lines:
        if line.strip().startswith("**关键词"):
            cn_keywords = parse_keyword(line, "关键词")
        else:
            cn_text_lines.append(line)
    for line in en_lines:
        if line.strip().startswith("**Keywords"):
            en_keywords = parse_keyword(line, "Keywords")
        else:
            en_text_lines.append(line)

    symbol_tables = [block.rows for block in parse_blocks(symbols_lines) if block.kind == "table" and block.rows]
    if not symbol_tables:
        raise RuntimeError("missing symbols table in article.md")

    return {
        "title": title,
        "cn_abstract": [block.text for block in parse_blocks(cn_text_lines) if block.kind == "paragraph"],
        "cn_keywords": cn_keywords,
        "en_abstract": [block.text for block in parse_blocks(en_text_lines) if block.kind == "paragraph"],
        "en_keywords": en_keywords,
        "symbols": symbol_tables[0],
        "body": parse_blocks(body_lines),
    }


def add_doc_field(paragraph, instr: str, placeholder: str = "") -> None:
    thesis.add_field(paragraph, instr, placeholder)


def add_toc(doc: Document) -> None:
    thesis.add_front_heading(doc, "目 录", 1)
    paragraph = doc.add_paragraph(style="Thesis TOC")
    thesis.set_paragraph_indent(paragraph, first_line_chars=0)
    add_doc_field(paragraph, r'TOC \o "1-3" \h \z \u')


def add_picture_block(doc: Document, rel_path: str, caption: str) -> None:
    path = (ARTICLE_DIR / rel_path).resolve()
    for _ in range(20):
        if path.exists():
            break
        time.sleep(0.25)
    if not path.exists():
        raise RuntimeError(f"missing image referenced by article.md: {rel_path}")
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.keep_with_next = True
    run = paragraph.add_run()
    with Image.open(path) as image:
        width_px, height_px = image.size
    max_width_cm = 14.8
    max_height_cm = 16.8
    if width_px and height_px and (height_px / width_px) * max_width_cm > max_height_cm:
        run.add_picture(str(path), height=Cm(max_height_cm))
    else:
        run.add_picture(str(path), width=Cm(max_width_cm))

    cap = doc.add_paragraph(style="Thesis Caption")
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.keep_with_next = False
    thesis.set_paragraph_indent(cap, first_line_chars=0)
    cap_run = cap.add_run(caption)
    thesis.set_run_font(cap_run, "宋体", "Times New Roman", 9, True)


def add_code_block(doc: Document, text: str) -> None:
    lines = text.splitlines() or [""]
    for line in lines:
        paragraph = doc.add_paragraph(style="Thesis Code")
        thesis.set_paragraph_indent(paragraph, first_line_chars=0)
        paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        run = paragraph.add_run(line if line else " ")
        thesis.set_run_font(run, "宋体", "Menlo", 8.5, False)
    doc.add_paragraph()


def add_paragraph(doc: Document, text: str, style: str = "Normal") -> None:
    if not text:
        return
    thesis.add_body_paragraph(doc, text, style=style)


def add_frontmatter(article: dict[str, object], doc: Document) -> None:
    doc.add_section(WD_SECTION_START.NEW_PAGE)
    thesis.configure_section(doc.sections[-1], page_fmt="upperRoman", start=1, header=True)

    thesis.add_front_heading(doc, "摘要", 1)
    for paragraph in article["cn_abstract"]:
        add_paragraph(doc, paragraph, style="Thesis Abstract CN")
    thesis.add_keywords(doc, "关键词：", str(article["cn_keywords"]), english=False)

    thesis.add_page_break(doc)
    thesis.add_front_heading(doc, "Abstract", 1)
    for paragraph in article["en_abstract"]:
        add_paragraph(doc, paragraph, style="Thesis Abstract EN")
    thesis.add_keywords(doc, "Keywords: ", str(article["en_keywords"]), english=True)

    thesis.add_page_break(doc)
    add_toc(doc)

    thesis.add_page_break(doc)
    thesis.add_front_heading(doc, "主要符号与缩略词", 1)
    thesis.add_table(doc, article["symbols"], "", "", "")


def start_body_section(doc: Document) -> None:
    doc.add_section(WD_SECTION_START.NEW_PAGE)
    thesis.configure_section(doc.sections[-1], page_fmt="decimal", start=1, header=True)


def render_body(article: dict[str, object], doc: Document) -> None:
    start_body_section(doc)
    seen_major = False
    current_section = ""
    for block in article["body"]:
        if block.kind == "heading":
            level = min(block.level, 3)
            page_break_before = False
            if block.level == 1:
                page_break_before = seen_major
                seen_major = True
                if block.text.startswith("参考文献"):
                    current_section = "references"
                elif block.text.startswith("附录"):
                    current_section = "appendix"
                else:
                    current_section = "body"
            heading_paragraph = thesis.add_heading(doc, block.text, level)
            if block.level == 1:
                heading_paragraph.paragraph_format.keep_with_next = False
                heading_paragraph.paragraph_format.page_break_before = page_break_before
        elif block.kind == "paragraph":
            style = "Normal"
            if current_section == "references":
                style = "Thesis Reference"
            elif current_section == "appendix":
                style = "Thesis Acknowledgement"
            add_paragraph(doc, block.text, style=style)
        elif block.kind == "table" and block.rows:
            thesis.add_table(doc, block.rows, "", "", "")
        elif block.kind == "image":
            add_picture_block(doc, block.path, block.text)
        elif block.kind == "code":
            add_code_block(doc, block.text)


def audit_output(docx_path: Path, article: dict[str, object]) -> None:
    with zipfile.ZipFile(docx_path) as zf:
        document_xml = zf.read("word/document.xml").decode("utf-8")
        styles_xml = zf.read("word/styles.xml").decode("utf-8")
        settings_xml = zf.read("word/settings.xml").decode("utf-8")
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    root = ET.fromstring(document_xml)
    paragraphs = ["".join(t.text or "" for t in p.findall(".//w:t", ns)) for p in root.findall(".//w:p", ns)]
    plain = "\n".join(paragraphs).replace("\u200b", "")

    required_text = [
        str(article["title"]).replace(" Web ", "Web"),
        "本人声明所呈交的论文（设计）",
        str(article["cn_abstract"][0])[:40],
        str(article["en_abstract"][0])[:40],
        "关键词：" + str(article["cn_keywords"]),
        "Keywords: " + str(article["en_keywords"]),
        "主要符号与缩略词",
        "参考文献",
        "附录 A 复现实验命令",
    ]
    for text in required_text:
        if text and text not in plain:
            raise RuntimeError(f"missing required output text: {text}")

    captions = [block.text for block in article["body"] if block.kind == "image"]
    missing_captions = [caption for caption in captions if caption not in plain]
    if missing_captions:
        raise RuntimeError(f"missing figure captions: {missing_captions}")

    for token in [
        'w:pgMar w:top="1701" w:right="1417" w:bottom="1417" w:left="1701"',
        'w:firstLineChars="200"',
        'w:styleId="TOC1"',
        'w:styleId="TOC2"',
        'w:styleId="TOC3"',
        'w:updateFields w:val="true"',
    ]:
        haystack = document_xml + styles_xml + settings_xml
        if token not in haystack:
            raise RuntimeError(f"missing required OOXML token: {token}")


def build() -> tuple[Path, Path]:
    article = split_article(ARTICLE_PATH.read_text(encoding="utf-8"))
    backup = backup_target()

    doc = Document()
    thesis.configure_styles(doc)
    thesis.add_cover(doc)
    thesis.add_declarations(doc)
    add_frontmatter(article, doc)
    render_body(article, doc)

    doc.core_properties.title = str(article["title"])
    doc.core_properties.author = thesis.AUTHOR
    doc.core_properties.subject = "北京林业大学本科毕业论文（设计）"

    tmp_path = TARGET_PATH.with_suffix(".tmp.docx")
    doc.save(tmp_path)
    thesis.update_settings_for_fields(tmp_path)
    thesis.patch_detector_ooxml(tmp_path)
    tmp_path.replace(TARGET_PATH)
    audit_output(TARGET_PATH, article)
    return TARGET_PATH, backup


if __name__ == "__main__":
    target, backup = build()
    print(f"wrote: {target}")
    print(f"backup: {backup}")
