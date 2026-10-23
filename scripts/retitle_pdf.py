# -*- coding: utf-8 -*-
"""Swap only the header job title on a copied master PDF. Does not rebuild the CV."""

from pathlib import Path

import pymupdf

LIBERATION_SERIF = Path("/usr/share/fonts/liberation/LiberationSerif-Regular.ttf")
HEADER_TITLES = (
    "SOFTWARE ENGINEER",
    "CLOUD ENGINEER",
    "MARKETING PROFESSIONAL",
    "FRONTEND DEVELOPER",
    "BACKEND DEVELOPER",
    "HARDWARE SUPPORT INTERN",
    "IT OFFICER",
    "ICT TECHNICIAN",
)


def retitle_pdf(src: Path, dest: Path, new_title: str) -> Path:
    """Replace the centered header title (under the applicant's name). Body text is left alone."""
    src, dest = Path(src), Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(src)
    page = doc[0]
    hits = []
    for needle in HEADER_TITLES:
        for r in page.search_for(needle):
            if r.y1 < 95:
                hits.append(r)
    if not hits:
        doc.close()
        raise ValueError(f"No header title to replace in {src}")
    union = hits[0]
    for r in hits[1:]:
        union |= r
    for r in hits:
        page.add_redact_annot(r, fill=(1, 1, 1))
    page.apply_redactions()
    title = " ".join(new_title.upper().split())
    fontfile = str(LIBERATION_SERIF)
    size = 12.49
    font = pymupdf.Font(fontfile=fontfile)
    width = font.text_length(title, fontsize=size)
    while width > 500 and size > 8:
        size -= 0.25
        width = font.text_length(title, fontsize=size)
    x = (page.rect.width - width) / 2
    y = union.y1 - 1.0
    page.insert_text((x, y), title, fontfile=fontfile, fontsize=size, color=(0, 0, 0))
    doc.save(dest)
    doc.close()
    return dest
