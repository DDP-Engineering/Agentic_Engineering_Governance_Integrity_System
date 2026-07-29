#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    generate_start_guide_pdf.py
@brief   Render the maintained AEGIS new-project guide as a styled PDF.
@details Parses the guide's constrained Markdown vocabulary and produces the
         distributable PDF without network access or host-office automation.
@author  Eng. Dan Dumitru Pasare
@date    2026-07-29
@version 1.0.1
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from typing import Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    REPOSITORY_ROOT
    / "05_Software"
    / "aegis"
    / "template"
    / ".agentic"
    / "documents"
    / "How_To_Start_A_New_Project.md"
)
DEFAULT_OUTPUT = DEFAULT_SOURCE.with_suffix(".pdf")

NAVY = colors.HexColor("#10243D")
BLUE = colors.HexColor("#204B73")
GOLD = colors.HexColor("#E1A01A")
GREEN = colors.HexColor("#29935E")
INK = colors.HexColor("#21364D")
MUTED = colors.HexColor("#61748A")
PALE = colors.HexColor("#F2F6FA")
LINE = colors.HexColor("#D9E3EC")

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------


def _register_fonts() -> None:
    """
    @brief Register Unicode-capable Windows fonts used by the guide.
    @return None.
    @exception FileNotFoundError Raised when the required fonts are unavailable.
    @version 1.0.0
    """

    font_directory = Path("C:/Windows/Fonts")
    regular = font_directory / "arial.ttf"
    bold = font_directory / "arialbd.ttf"
    mono = font_directory / "consola.ttf"
    missing = [path for path in (regular, bold, mono) if not path.is_file()]
    if missing:
        missing_text = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"required PDF fonts are unavailable: {missing_text}")

    pdfmetrics.registerFont(TTFont("AegisSans", str(regular)))
    pdfmetrics.registerFont(TTFont("AegisSansBold", str(bold)))
    pdfmetrics.registerFont(TTFont("AegisMono", str(mono)))
    pdfmetrics.registerFontFamily(
        "AegisSans",
        normal="AegisSans",
        bold="AegisSansBold",
    )


def _build_styles() -> dict[str, ParagraphStyle]:
    """
    @brief Build the paragraph styles used by the PDF renderer.
    @return A mapping from semantic style names to ReportLab styles.
    @version 1.0.0
    """

    sample = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body",
        parent=sample["BodyText"],
        fontName="AegisSans",
        fontSize=9.5,
        leading=14.2,
        textColor=INK,
        spaceAfter=5,
    )
    return {
        "body": body,
        "section": ParagraphStyle(
            "Section",
            parent=sample["Heading2"],
            fontName="AegisSansBold",
            fontSize=17,
            leading=21,
            textColor=NAVY,
            spaceBefore=11,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=sample["Title"],
            fontName="AegisSansBold",
            fontSize=31,
            leading=36,
            textColor=colors.white,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=body,
            fontSize=13,
            leading=19,
            textColor=colors.HexColor("#DDE8F2"),
        ),
        "code": ParagraphStyle(
            "Code",
            fontName="AegisMono",
            fontSize=8.1,
            leading=11.2,
            textColor=NAVY,
            leftIndent=7,
            rightIndent=7,
            spaceBefore=3,
            spaceAfter=7,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=body,
            leftIndent=14,
            firstLineIndent=-8,
            bulletIndent=4,
            spaceAfter=3,
        ),
        "number": ParagraphStyle(
            "Number",
            parent=body,
            leftIndent=18,
            firstLineIndent=-12,
            bulletIndent=3,
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=body,
            fontSize=8,
            leading=11,
            textColor=MUTED,
        ),
    }


def _inline_markup(value: str) -> str:
    """
    @brief Convert the guide's inline-code syntax to ReportLab markup.
    @param[in] value Plain Markdown text.
    @return XML-safe ReportLab paragraph markup.
    @version 1.0.0
    """

    escaped = html.escape(value)
    return re.sub(
        r"`([^`]+)`",
        (
            lambda match: (
                '<font name="AegisMono" color="#204B73">'
                f"{match.group(1)}</font>"
            )
        ),
        escaped,
    )


def _page_decoration(canvas, document: BaseDocTemplate) -> None:
    """
    @brief Draw the cover background and repeated page chrome.
    @param[in,out] canvas ReportLab page canvas.
    @param[in] document Active document state.
    @return None.
    @version 1.0.0
    """

    width, height = A4
    canvas.saveState()
    if document.page == 1:
        canvas.setFillColor(NAVY)
        canvas.rect(0, 0, width, height, stroke=0, fill=1)
        canvas.setFillColor(GOLD)
        canvas.rect(18 * mm, height - 31 * mm, 26 * mm, 2.2 * mm, stroke=0, fill=1)
    else:
        canvas.setFillColor(NAVY)
        canvas.rect(0, height - 17 * mm, width, 17 * mm, stroke=0, fill=1)
        canvas.setFont("AegisSansBold", 8)
        canvas.setFillColor(colors.white)
        canvas.drawString(18 * mm, height - 10.5 * mm, "AEGIS 2.0  |  START GUIDE")
        canvas.setStrokeColor(LINE)
        canvas.line(18 * mm, 15 * mm, width - 18 * mm, 15 * mm)
        canvas.setFont("AegisSans", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(
            18 * mm,
            9.5 * mm,
            "DDP Engineering  |  Schema 3  |  Offline-first",
        )
        canvas.drawRightString(width - 18 * mm, 9.5 * mm, str(document.page - 1))
    canvas.restoreState()


def _page_decoration_end(canvas, document: BaseDocTemplate) -> None:
    """
    @brief Redraw non-cover page chrome above split flowables.
    @param[in,out] canvas ReportLab page canvas.
    @param[in] document Active document state.
    @return None.
    @version 1.0.0
    """

    if document.page != 1:
        _page_decoration(canvas, document)


def _code_box(code: str, style: ParagraphStyle) -> Table:
    """
    @brief Wrap a fenced code block in the guide's visual container.
    @param[in] code Code content without fence markers.
    @param[in] style Preformatted text style.
    @return A styled single-cell table.
    @version 1.0.0
    """

    box = Table([[Preformatted(code, style)]], colWidths=[A4[0] - 42 * mm])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return box


def _section_heading(text: str, style: ParagraphStyle) -> Flowable:
    """
    @brief Build a section heading with the gold guide marker.
    @param[in] text Heading text without Markdown markers.
    @param[in] style Heading paragraph style.
    @return A keep-together heading block.
    @version 1.0.0
    """

    heading = Table(
        [["", Paragraph(_inline_markup(text), style)]],
        colWidths=[3 * mm, A4[0] - 45 * mm],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), GOLD),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (1, 0), (1, 0), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )
    return KeepTogether([Spacer(1, 2 * mm), heading])


def _cover(styles: dict[str, ParagraphStyle]) -> list[Flowable]:
    """
    @brief Build the AEGIS 2.0 cover page.
    @param[in] styles Semantic paragraph styles.
    @return Cover flowables ending with a page break.
    @version 1.0.0
    """

    eyebrow = ParagraphStyle(
        "Eyebrow",
        parent=styles["small"],
        fontName="AegisSansBold",
        fontSize=11,
        textColor=GOLD,
        spaceAfter=12,
    )
    badge_label = ParagraphStyle(
        "BadgeLabel",
        parent=styles["small"],
        fontSize=8,
        textColor=colors.HexColor("#BFD0E0"),
    )
    badge_value = ParagraphStyle(
        "BadgeValue",
        parent=styles["body"],
        textColor=colors.white,
        alignment=1,
    )
    schema_value = ParagraphStyle(
        "SchemaValue",
        parent=badge_value,
        fontSize=20,
    )
    badge = Table(
        [
            [
                Paragraph("SCHEMA", badge_label),
                Paragraph("INTERFACE", badge_label),
                Paragraph("DEFAULT CHECKS", badge_label),
            ],
            [
                Paragraph("<b>3</b>", schema_value),
                Paragraph("<b>Stage forms</b>", badge_value),
                Paragraph("<b>External</b>", badge_value),
            ],
        ],
        colWidths=[38 * mm, 55 * mm, 55 * mm],
        rowHeights=[9 * mm, 18 * mm],
    )
    badge.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BLUE),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#4C6C89")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#4C6C89")),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    flow = ParagraphStyle(
        "Flow",
        parent=styles["small"],
        fontName="AegisSansBold",
        fontSize=8.5,
        leading=13,
        textColor=colors.white,
    )
    boundary = ParagraphStyle(
        "Boundary",
        parent=styles["small"],
        fontSize=8.5,
        textColor=colors.HexColor("#BFD0E0"),
    )
    return [
        Spacer(1, 41 * mm),
        Paragraph("AEGIS 2.0", eyebrow),
        Paragraph("How to Start and Adapt<br/>a New Project", styles["cover_title"]),
        Spacer(1, 10 * mm),
        Paragraph(
            "A file-first operating guide for the eight-stage workflow, "
            "deterministic verification, and explicit human approval.",
            styles["cover_subtitle"],
        ),
        Spacer(1, 15 * mm),
        badge,
        Spacer(1, 37 * mm),
        Paragraph(
            "INTAKE > ALIGNMENT > REQUIREMENT > DESIGN > CHECK > "
            "IMPLEMENTATION > VALIDATION > DELIVERY",
            flow,
        ),
        Spacer(1, 4 * mm),
        Paragraph(
            "No migration from schema 2. No compatibility reader for AEGIS 1.x.",
            boundary,
        ),
        PageBreak(),
    ]


def _content_flow(
    source: Path,
    styles: dict[str, ParagraphStyle],
) -> list[Flowable]:
    """
    @brief Parse the maintained Markdown guide into PDF flowables.
    @param[in] source Markdown source path.
    @param[in] styles Semantic paragraph styles.
    @return Flowables for the guide body.
    @version 1.0.0
    """

    flowables: list[Flowable] = []
    paragraph_lines: list[str] = []
    list_items: list[tuple[str, str]] = []
    list_kind: str | None = None
    code_lines: list[str] = []
    in_comment = False
    in_code = False

    def flush_paragraph() -> None:
        """@brief Append buffered prose. @version 1.0.0"""

        if paragraph_lines:
            text = " ".join(part.strip() for part in paragraph_lines)
            flowables.append(Paragraph(_inline_markup(text), styles["body"]))
            paragraph_lines.clear()

    def flush_list() -> None:
        """@brief Append buffered ordered or unordered items. @version 1.0.0"""

        nonlocal list_kind
        if list_items:
            for marker, value in list_items:
                if list_kind == "ordered":
                    flowables.append(
                        Paragraph(
                            _inline_markup(value),
                            styles["number"],
                            bulletText=f"{marker}.",
                        )
                    )
                else:
                    flowables.append(
                        Paragraph(
                            _inline_markup(value),
                            styles["bullet"],
                            bulletText="-",
                        )
                    )
            list_items.clear()
        list_kind = None

    lines = source.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()
        if stripped.startswith("<!--"):
            in_comment = True
        if in_comment:
            if "-->" in stripped:
                in_comment = False
            index += 1
            continue
        if stripped.startswith("# "):
            index += 1
            continue
        if stripped.startswith("```"):
            flush_paragraph()
            flush_list()
            if in_code:
                flowables.append(_code_box("\n".join(code_lines), styles["code"]))
                code_lines = []
            in_code = not in_code
            index += 1
            continue
        if in_code:
            code_lines.append(raw)
            index += 1
            continue
        if stripped.startswith("## "):
            flush_paragraph()
            flush_list()
            flowables.append(_section_heading(stripped[3:], styles["section"]))
            index += 1
            continue

        ordered = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        unordered = re.match(r"^-\s+(.*)$", stripped)
        if ordered or unordered:
            flush_paragraph()
            kind = "ordered" if ordered else "unordered"
            if list_kind and list_kind != kind:
                flush_list()
            list_kind = kind
            marker = ordered.group(1) if ordered else ""
            value = ordered.group(2) if ordered else unordered.group(1)
            continuation = index + 1
            while continuation < len(lines):
                next_raw = lines[continuation]
                if next_raw.startswith("   ") and next_raw.strip():
                    value += " " + next_raw.strip()
                    continuation += 1
                else:
                    break
            list_items.append((marker, value))
            index = continuation
            continue

        if not stripped:
            flush_paragraph()
            flush_list()
            flowables.append(Spacer(1, 1.5 * mm))
        else:
            paragraph_lines.append(stripped)
        index += 1

    flush_paragraph()
    flush_list()
    return flowables


def generate_pdf(source: Path, output: Path) -> None:
    """
    @brief Generate the styled start-guide PDF from its Markdown source.
    @param[in] source Maintained Markdown guide.
    @param[in] output Destination PDF path.
    @return None.
    @exception FileNotFoundError Raised when the source or fonts are unavailable.
    @version 1.0.0
    """

    if not source.is_file():
        raise FileNotFoundError(f"guide source does not exist: {source}")
    _register_fonts()
    styles = _build_styles()
    frame = Frame(
        18 * mm,
        19 * mm,
        A4[0] - 36 * mm,
        A4[1] - 41 * mm,
        id="content",
    )
    document = BaseDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=19 * mm,
        title="How To Start and Adapt a New Project with AEGIS 2.0",
        author="DDP Engineering",
        subject="AEGIS 2.0 stage-oriented workflow and schema-3 workspace guide",
    )
    document.addPageTemplates(
        [
            PageTemplate(
                id="main",
                frames=[frame],
                onPage=_page_decoration,
                onPageEnd=_page_decoration_end,
            )
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    document.build(_cover(styles) + _content_flow(source, styles))


def _parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    """
    @brief Parse command-line arguments for the documentation generator.
    @param[in] arguments Optional argument sequence for tests or embedding.
    @return Parsed command-line namespace.
    @version 1.0.0
    """

    parser = argparse.ArgumentParser(
        description="Generate the AEGIS 2.0 start-guide PDF.",
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(arguments)


# -----------------------------------------------------------------------------
# PUBLIC API
# -----------------------------------------------------------------------------


def main(arguments: Sequence[str] | None = None) -> int:
    """
    @brief Generate the configured PDF and print its destination.
    @param[in] arguments Optional argument sequence.
    @return Process exit status.
    @version 1.0.0
    """

    options = _parse_arguments(arguments)
    generate_pdf(options.source.resolve(), options.output.resolve())
    print(options.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
