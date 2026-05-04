"""Generate a one-page (or multi-page) health summary PDF from user + symptom + diet data."""
from __future__ import annotations

import os
import platform
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Optional, Tuple
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

PAGE_W, PAGE_H = A4
MARGIN_X = 1.8 * cm
HEADER_H = 2.55 * cm
FOOTER_H = 1.35 * cm


def _resolve_unicode_font() -> Tuple[Optional[str], Optional[str]]:
    """Return (regular_ttf_path, bold_ttf_path) for Unicode body text, or (None, None) for built-in Helvetica."""
    if platform.system() == "Windows":
        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        fonts = windir / "Fonts"
        reg = fonts / "calibri.ttf"
        bold = fonts / "calibrib.ttf"
        if reg.is_file():
            return (str(reg), str(bold) if bold.is_file() else str(reg))
        arial = fonts / "arial.ttf"
        ab = fonts / "arialbd.ttf"
        if arial.is_file():
            return (str(arial), str(ab) if ab.is_file() else str(arial))
    elif platform.system() == "Darwin":
        for reg in (
            Path("/Library/Fonts/Arial.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        ):
            if reg.is_file():
                bold = reg.parent / "Arial Bold.ttf"
                return (str(reg), str(bold) if bold.is_file() else str(reg))
    else:
        for reg in (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
        ):
            if reg.is_file():
                bold = reg.with_name("DejaVuSans-Bold.ttf")
                return (str(reg), str(bold) if bold.is_file() else str(reg))
    return (None, None)


def _register_fonts() -> Tuple[str, str]:
    reg_path, bold_path = _resolve_unicode_font()
    if reg_path:
        try:
            pdfmetrics.registerFont(TTFont("MedBody", reg_path))
            pdfmetrics.registerFont(TTFont("MedBody-Bold", bold_path or reg_path))
            return "MedBody", "MedBody-Bold"
        except Exception:
            pass
    return "Helvetica", "Helvetica-Bold"


def _esc(text: Any) -> str:
    if text is None:
        return ""
    return escape(str(text))


def _draw_header(canvas: Any, page_num: int) -> None:
    canvas.saveState()
    # Brand strip (teal, aligned with app theme)
    canvas.setFillColorRGB(4 / 255, 124 / 255, 140 / 255)
    canvas.rect(0, PAGE_H - HEADER_H, PAGE_W, HEADER_H, fill=1, stroke=0)
    # Logo mark: solid teal rounded tile + white cross (matches simple web favicon / search-style medical icon)
    x0, y0 = 1.15 * cm, PAGE_H - HEADER_H + 0.52 * cm
    lw, lh = 0.88 * cm, 0.88 * cm
    canvas.setFillColorRGB(4 / 255, 124 / 255, 140 / 255)
    canvas.roundRect(x0, y0, lw, lh, 3.5, fill=1, stroke=0)
    mx, my = x0 + lw / 2, y0 + lh / 2
    canvas.setStrokeColorRGB(1, 1, 1)
    canvas.setLineWidth(2.0)
    canvas.line(x0 + 0.2 * cm, my, x0 + lw - 0.2 * cm, my)
    canvas.line(mx, y0 + 0.2 * cm, mx, y0 + lh - 0.2 * cm)
    canvas.setFillColorRGB(1, 1, 1)
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(2.35 * cm, PAGE_H - HEADER_H + 0.95 * cm, "AI Medical Assistant")
    canvas.setFont("Helvetica", 9.5)
    canvas.drawString(2.35 * cm, PAGE_H - HEADER_H + 0.58 * cm, "Personal health summary report")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(PAGE_W - 1.1 * cm, PAGE_H - HEADER_H + 0.62 * cm, f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    if page_num > 1:
        canvas.drawRightString(PAGE_W - 1.1 * cm, PAGE_H - HEADER_H + 0.38 * cm, f"Page {page_num}")
    canvas.restoreState()


def _draw_footer(canvas: Any) -> None:
    canvas.saveState()
    canvas.setStrokeColorRGB(0.75, 0.86, 0.91)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN_X, FOOTER_H + 0.55 * cm, PAGE_W - MARGIN_X, FOOTER_H + 0.55 * cm)
    canvas.setFillColorRGB(0.29, 0.42, 0.51)
    canvas.setFont("Helvetica", 8.5)
    canvas.drawCentredString(PAGE_W / 2, 0.82 * cm, "\xa9 Dishanth Naik  |  AI Medical Assistant")
    canvas.setFont("Helvetica", 7.5)
    canvas.drawCentredString(PAGE_W / 2, 0.48 * cm, "Educational information only \u2014 not a medical diagnosis or treatment plan.")
    canvas.restoreState()


def _page(canvas: Any, doc: Any) -> None:
    n = canvas.getPageNumber()
    _draw_header(canvas, n)
    _draw_footer(canvas)


def build_health_report_pdf(
    *,
    user_name: str,
    user_email: str,
    age: Optional[int],
    weight_kg: Optional[float],
    height_cm: Optional[float],
    medical_history: Optional[str],
    symptom: str,
    condition: str,
    doctor_type: str,
    precautions: list[str],
    symptom_disclaimer: str,
    diet: dict[str, Any],
) -> bytes:
    body_font, body_bold = _register_fonts()
    styles = getSampleStyleSheet()
    normal = ParagraphStyle(
        "MedNormal",
        parent=styles["Normal"],
        fontName=body_font,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#0a2342"),
        spaceAfter=6,
    )
    heading = ParagraphStyle(
        "MedHeading",
        parent=styles["Heading2"],
        fontName=body_bold,
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor("#047c8c"),
        spaceBefore=10,
        spaceAfter=6,
        alignment=TA_LEFT,
    )
    small = ParagraphStyle(
        "MedSmall",
        parent=normal,
        fontSize=8.8,
        leading=12,
        textColor=colors.HexColor("#4a6b82"),
    )
    box = ParagraphStyle(
        "MedBox",
        parent=normal,
        backColor=colors.HexColor("#e8f4f8"),
        borderColor=colors.HexColor("#c5dce8"),
        borderWidth=0.5,
        borderPadding=8,
        spaceBefore=4,
        spaceAfter=8,
    )

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=HEADER_H + 0.85 * cm,
        bottomMargin=FOOTER_H + 1.1 * cm,
        title="Health summary report",
        author="AI Medical Assistant",
    )

    story: list[Any] = []

    def p(txt: str, style=normal) -> Paragraph:
        return Paragraph(_esc(txt).replace("\n", "<br/>"), style)

    # Section markers (Unicode; system TTF when available for full glyph coverage)
    story.append(Paragraph("\u25B6  Patient details", heading))
    u_lines = [
        f"<b>Name:</b> {_esc(user_name)}",
        f"<b>Email:</b> {_esc(user_email)}",
    ]
    if age is not None:
        u_lines.append(f"<b>Age:</b> {_esc(age)}")
    if weight_kg is not None:
        u_lines.append(f"<b>Weight:</b> {_esc(weight_kg)} kg")
    if height_cm is not None:
        u_lines.append(f"<b>Height:</b> {_esc(height_cm)} cm")
    story.append(Paragraph("<br/>".join(u_lines), normal))
    if medical_history and str(medical_history).strip():
        story.append(Paragraph(f"<b>Medical history notes:</b> {_esc(medical_history)}", small))

    story.append(Paragraph("\u25B6  Reported symptom", heading))
    story.append(p(symptom))

    story.append(
        Paragraph(
            "\u25B6  AI-oriented condition summary <font size='9' color='#4a6b82'>(not a diagnosis)</font>",
            heading,
        )
    )
    story.append(p(condition))

    story.append(Paragraph("\u25B6  Suggested doctor type", heading))
    story.append(p(doctor_type))

    story.append(Paragraph("\u25B6  Precautions", heading))
    if precautions:
        items = [ListItem(Paragraph(_esc(x), normal), leftIndent=12) for x in precautions]
        story.append(
            ListFlowable(
                items,
                bulletType="bullet",
                leftIndent=18,
                bulletFontName=body_font,
                bulletFontSize=9,
            )
        )
    else:
        story.append(p("None listed."))

    story.append(
        Paragraph(
            "\u25B6  Recommended diet plan <font size='9' color='#4a6b82'>(general guidance)</font>",
            heading,
        )
    )

    def diet_block(title: str, items: list[str]) -> None:
        story.append(Paragraph(f"<b>{_esc(title)}</b>", normal))
        if items:
            lst = [ListItem(Paragraph(_esc(i), normal), leftIndent=10) for i in items[:14]]
            story.append(
                ListFlowable(
                    lst,
                    bulletType="bullet",
                    leftIndent=16,
                    bulletFontName=body_font,
                    bulletFontSize=9,
                )
            )
        story.append(Spacer(1, 4))

    diet_block("Foods to emphasize", list(diet.get("recommended_foods") or []))
    diet_block("Foods to limit or avoid", list(diet.get("foods_to_avoid") or []))
    diet_block("Healthy habits", list(diet.get("healthy_habits") or []))

    story.append(Paragraph("\u26A0  Disclaimer", heading))
    disc_parts = [_esc(symptom_disclaimer)]
    dd = diet.get("disclaimer")
    if dd and str(dd).strip():
        disc_parts.append(_esc(dd))
    story.append(Paragraph("<br/><br/>".join(disc_parts), box))

    doc.build(story, onFirstPage=_page, onLaterPages=_page)
    out = buf.getvalue()
    buf.close()
    return out
