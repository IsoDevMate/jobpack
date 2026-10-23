# -*- coding: utf-8 -*-
"""Convert a tailored .docx to PDF via mammoth HTML + Chrome (no font overlay)."""

from pathlib import Path
import re
import subprocess
import tempfile

import mammoth

ROOT = Path(__file__).resolve().parents[1]

import sys
sys.path.insert(0, str(ROOT / "scripts"))
from userconfig import link_map  # noqa: E402

CSS = """
@page { size: Letter; margin: 0.75in 0.75in 0.625in 0.625in; }
html, body { font-family: "Times New Roman", Times, serif; font-size: 10.5pt; line-height: 1.35; color: #000; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
h1, h2, h3, p { margin: 0 0 0.35em 0; }
a, a:visited { color: #1155CC !important; text-decoration: underline !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
/* Header: name, title, contact centered */
.cv-name {
  text-align: center;
  font-size: 22pt;
  font-weight: bold;
  letter-spacing: 0.06em;
  margin: 0 0 0.08em 0;
  line-height: 1.15;
}
.cv-title {
  text-align: center;
  font-size: 12pt;
  font-weight: bold;
  letter-spacing: 0.04em;
  margin: 0 0 0.2em 0;
}
.cv-contact {
  text-align: center;
  font-size: 10pt;
  margin: 0 0 0.85em 0;
}
.cv-section {
  font-weight: bold;
  font-size: 11pt;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  border-bottom: 1px solid #000;
  margin: 0.7em 0 0.4em 0;
  padding-bottom: 0.12em;
}
/* Word right-tab -> date flush right */
.job-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 16px;
}
.job-left { flex: 1; min-width: 0; }
.job-date { white-space: nowrap; font-weight: bold; }
/* Never strand a new role heading/subtitle at the bottom of a page. */
.job-head { break-after: avoid-page; page-break-after: avoid; }
.job-head + p { break-after: avoid-page; page-break-after: avoid; }
.job-head + p + ul { break-inside: avoid-page; page-break-inside: avoid; }
"""


_SECTIONS = {"experience", "education", "skills", "certifications"}


def _mark_header_and_sections(html: str) -> str:
    """Mammoth drops Word centering. Restore header + underlined sections."""
    count = {"n": 0}

    def repl(m):
        inner = m.group(1)
        n = count["n"]
        count["n"] += 1
        if n == 0:
            return f'<p class="cv-name">{inner}</p>'
        if n == 1:
            return f'<p class="cv-title">{inner}</p>'
        if n == 2:
            return f'<p class="cv-contact">{inner}</p>'
        plain = re.sub(r"<[^>]+>", "", inner).strip().lower()
        if plain in _SECTIONS:
            return f'<p class="cv-section">{plain.upper()}</p>'
        return m.group(0)

    return re.sub(r"<p>(.*?)</p>", repl, html, flags=re.DOTALL)


def _dates_flush_right(html: str) -> str:
    """Turn a Word right-tab inside a <p> into a flex row so Chrome keeps the date on the right."""

    def repl(m):
        left, right = m.group(1), m.group(2)
        if not right.strip():
            return m.group(0)
        return (
            f'<p class="job-head"><span class="job-left">{left}</span>'
            f'<span class="job-date">{right}</span></p>'
        )

    # Tab must stay inside one <p>. A greedy .* crosses </p> and steals later dates.
    return re.sub(r"<p>((?:(?!</p>).)*?)\t((?:(?!</p>).)*?)</p>", repl, html)


def _inject_verified_links(html: str) -> str:
    """Add canonical links when a legacy DOCX contains labels but no hyperlink relationships.

    The (label, url) table comes from profile/user.json so a new user gets their
    own links injected, not the project author's.
    """
    for label, url in link_map():
        if f'href="{url}"' not in html:
            html = html.replace(label, f'<a href="{url}">{label}</a>', 1)
    return html


def docx_to_pdf(docx_path: Path, pdf_path: Path):
    docx_path = Path(docx_path)
    pdf_path = Path(pdf_path)
    result = mammoth.convert_to_html(str(docx_path))
    body = _dates_flush_right(_mark_header_and_sections(_inject_verified_links(result.value)))
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
    <style>{CSS}</style></head><body>{body}</body></html>"""
    with tempfile.TemporaryDirectory() as td:
        html_path = Path(td) / "cv.html"
        html_path.write_text(html, encoding="utf-8")
        chrome = "/usr/bin/google-chrome-stable"
        cmd = [
            chrome,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            str(html_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    return pdf_path
