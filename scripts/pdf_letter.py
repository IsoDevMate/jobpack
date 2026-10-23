# -*- coding: utf-8 -*-
"""Cover letter PDF in the gold shape. Never mentions missing skills.

Header/footer/contact lines come from profile/user.json (via userconfig).
"""

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

try:
    from userconfig import load as _load
except ImportError:  # running as a script from scripts/
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from userconfig import load as _load


def _plain(text: str) -> str:
    """Human cover-letter text: no em/en dashes (AI tell). Use ASCII hyphen only."""
    text = text.replace("\u2014", "-").replace("\u2013", "-")  # em, en
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    return text


def write_cover_letter(path, *, date, body_paras, company_lines=None, inside=None, salutation="Dear Hiring Team,", closing=None):
    cfg = _load()
    if company_lines is None:
        company_lines = inside or []
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    date = _plain(date)
    company_lines = [_plain(x) for x in company_lines]
    salutation = _plain(salutation)
    body_paras = [_plain(p) for p in body_paras]
    doc = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
        topMargin=0.8 * inch,
        bottomMargin=0.8 * inch,
    )
    normal = ParagraphStyle(
        "n",
        fontName="Times-Roman",
        fontSize=11,
        leading=16,
        spaceAfter=10,
    )
    name = ParagraphStyle("name", parent=normal, fontName="Times-Bold", fontSize=13, spaceAfter=2)
    small = ParagraphStyle("s", parent=normal, fontSize=11, spaceAfter=2, leading=14)
    story = [
        Paragraph(_plain(cfg["full_name"]), name),
        Paragraph(_plain(cfg["phone"]), small),
        Paragraph(_plain(cfg["email"]), small),
        Paragraph(_plain(cfg["city"]), ParagraphStyle("city", parent=small, spaceAfter=12)),
        Paragraph(date, normal),
    ]
    for line in company_lines:
        story.append(Paragraph(line, small))
    story.append(Spacer(1, 10))
    story.append(Paragraph(salutation, normal))
    for para in body_paras:
        story.append(Paragraph(para, normal))
    story.append(Paragraph("Thank you for your time. I look forward to your response.", normal))
    story.append(Paragraph("Yours sincerely,", normal))
    story.append(Paragraph(_plain(cfg["full_name"]), small))
    story.append(Paragraph(_plain(cfg["phone"]), small))
    story.append(Paragraph(_plain(cfg["email"]), small))
    doc.build(story)
