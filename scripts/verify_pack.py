# -*- coding: utf-8 -*-
"""
Mandatory post-generate verification. CLEAR TO SEND is illegal without this.

Process:
1. pdftotext the real Resume + Cover Letter PDFs
2. Render resume page 1 to preview.png (visual evidence)
3. Apply role-profile rules to extracted text
4. Write VERIFY.txt with every PASS/FAIL
5. Exit non-zero / return ok=False if any FAIL

The agent must Read preview.png + VERIFY.txt before telling the user CLEAR.
Contact/required-link values come from profile/user.json (userconfig).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import userconfig  # noqa: E402


def _pdftotext(path: Path) -> str:
    r = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True)
    return r.stdout or ""


def _pdf_urls(path: Path) -> set[str]:
    """Read actual clickable PDF annotations, not merely visible URL text."""
    result = subprocess.run(["pdfinfo", "-url", str(path)], capture_output=True, text=True)
    urls = set()
    for line in (result.stdout or "").splitlines():
        match = re.search(r"(?:Annotation|Action)\s+(\S+)$", line.strip())
        if match:
            urls.add(match.group(1).rstrip("/"))
    return urls


def _orphan_role_pages(path: Path) -> list[int]:
    """Find pages ending with only a role heading and subtitle, with bullets on the next page."""
    try:
        import pymupdf
    except ImportError:
        return []
    doc = pymupdf.open(path)
    orphaned = []
    role_words = re.compile(r"\b(engineer|developer|officer|manager|intern|consultant|technician|writer)\b", re.I)
    subtitle_words = re.compile(r"\b(platform|system|tool|architecture|development|infrastructure|consulting)\b", re.I)
    for index, page in enumerate(doc[:-1]):
        lines = [line.strip() for line in page.get_text().splitlines() if line.strip()]
        if len(lines) >= 2 and role_words.search(lines[-2]) and subtitle_words.search(lines[-1]):
            orphaned.append(index + 1)
    doc.close()
    return orphaned


def render_page1(pdf: Path, dest_png: Path) -> bool:
    """Write first page PNG so the agent (and user) can visually inspect."""
    try:
        import pymupdf
    except ImportError:
        # fallback: pdftoppm if present
        out = subprocess.run(
            ["pdftoppm", "-png", "-f", "1", "-l", "1", "-singlefile", str(pdf), str(dest_png.with_suffix(""))],
            capture_output=True,
            text=True,
        )
        return out.returncode == 0 and dest_png.exists()

    doc = pymupdf.open(pdf)
    page = doc[0]
    # ~150 DPI equivalent zoom
    pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
    dest_png.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(dest_png))
    doc.close()
    return dest_png.exists() and dest_png.stat().st_size > 1000


def role_profile(job_title: str, jd: str) -> str:
    blob = f"{job_title}\n{jd}".lower()
    if any(
        x in blob
        for x in (
            "ict technician",
            "digital workplace",
            "it officer",
            "hardware support",
            "help desk",
            "helpdesk",
            "desktop support",
            "ict attachment",
            "ict clerk",
            "it manager",
            "ict manager",
        )
    ):
        return "ict"
    if any(x in blob for x in ("marketing", "social media", "tiktok", "content creator", "brand")):
        return "marketing"
    return "software"


def run_checks(*, resume: Path, letter: Path, job_title: str, jd: str) -> list[dict]:
    rt = _pdftotext(resume)
    lt = _pdftotext(letter)
    rt_l, lt_l = rt.lower(), lt.lower()
    header = rt_l.split("experience", 1)[0] if "experience" in rt_l else rt_l[:500]
    profile = role_profile(job_title, jd)
    cfg = userconfig.load()
    checks = []

    def add(name, ok, detail):
        checks.append({"name": name, "result": "PASS" if ok else "FAIL", "detail": detail})

    add("V1 resume PDF exists and non-empty", resume.exists() and resume.stat().st_size > 5000, str(resume))
    add("V2 letter PDF exists and non-empty", letter.exists() and letter.stat().st_size > 1000, str(letter))
    add("V3 header contains job title words", any(w in header for w in job_title.lower().split()[:3] if len(w) > 3), job_title)

    urls = _pdf_urls(resume)
    if profile == "software":
        required = userconfig.required_links(cfg)
        if required:
            missing_links = sorted(required - urls)
            add("V3a software contact links are clickable", not missing_links, "missing: " + repr(missing_links))
            employer_links = [u for u in urls if u.startswith("http") and u not in required]
            add("V3b employer names have clickable links", len(employer_links) >= 2, f"employer links: {len(employer_links)}")
    orphan_pages = _orphan_role_pages(resume)
    add("V3c no orphan role heading at page bottom", not orphan_pages, f"orphan pages: {orphan_pages}")

    # Letter global
    add("V4 letter Yours sincerely", "yours sincerely" in lt_l, "gold close")
    add("V5 letter no I want this role because", "i want this role because" not in lt_l, "banned phrase")
    add("V6 letter no em/en dash", "\u2014" not in lt and "\u2013" not in lt, "ASCII hyphen only")
    add("V7 letter has company or hiring team", "hiring" in lt_l or job_title.lower().split()[0] in lt_l, "addressed")

    recent = str(cfg.get("recent_year") or "")
    if profile == "ict":
        add(
            "V8 ICT header no LinkedIn/GitHub/Portfolio",
            "linkedin" not in header and "github" not in header and "portfolio" not in header,
            "SWE links forbidden on ICT packs",
        )
        add(
            "V9 ICT no DevOps/SWE noise",
            all(x not in rt_l for x in ("kubernetes", "terraform", "openai", "nestjs", "backend & devops")),
            "must not ship SWE annotator master",
        )
        evidence = [e for e in (cfg.get("ict_evidence") or []) if e]
        add(
            "V10 ICT shows real support work",
            any(x in rt_l for x in evidence) if evidence else "support" in rt_l,
            "real ICT/support experience required",
        )
    elif profile == "marketing":
        add(
            "V8 marketing header no SWE LinkedIn URL",
            "linkedin.com/in/" not in header,
            "no SWE LinkedIn on marketing header",
        )
    else:  # software
        add(
            "V8 software has a recent role signal",
            (recent in rt_l) if recent else ("present" in rt_l or "now" in rt_l),
            f"do not ship a stale master that tops out before {recent or 'now'}",
        )
        if "full stack" in f"{job_title} {jd}".lower() or "fullstack" in f"{job_title} {jd}".lower():
            recent_employer_ok = bool(recent and recent in rt_l)
            add("V9 fullstack not FE-only master", recent_employer_ok or "founding engineer" in rt_l, "use the full software-engineer master")

    return checks


def verify_pack(*, pack_dir: Path, resume: Path, letter: Path, job_title: str, jd: str) -> dict:
    pack_dir = Path(pack_dir)
    pack_dir.mkdir(parents=True, exist_ok=True)
    preview = pack_dir / "preview.png"
    rendered = render_page1(resume, preview)
    checks = run_checks(resume=resume, letter=letter, job_title=job_title, jd=jd)
    checks.insert(
        0,
        {
            "name": "V0 resume page-1 preview.png rendered",
            "result": "PASS" if rendered else "FAIL",
            "detail": str(preview) if rendered else "pymupdf/pdftoppm failed - cannot claim visual verify",
        },
    )

    rt_head = "\n".join(_pdftotext(resume).splitlines()[:12])
    lines = [
        "# VERIFY - source of truth (extracted from PDFs you generated)",
        f"# pack: {pack_dir.name}",
        f"# title: {job_title}",
        f"# profile: {role_profile(job_title, jd)}",
        f"# preview: {preview.name if rendered else 'MISSING'}",
        "",
        "## Resume header extract",
        rt_head,
        "",
        "## Checks",
    ]
    for c in checks:
        lines.append(f"- [{c['result']}] {c['name']} — {c['detail']}")
    fails = [c for c in checks if c["result"] == "FAIL"]
    lines += [
        "",
        f"## Verdict: {'VERIFY PASS' if not fails else 'VERIFY FAIL'}",
        f"failed: {len(fails)}",
        "",
        "Agent rule: Read preview.png with the Read tool. Do not tell the user CLEAR if VERIFY FAIL.",
    ]
    verify_path = pack_dir / "VERIFY.txt"
    verify_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": len(fails) == 0,
        "fails": [c["name"] for c in fails],
        "checks": checks,
        "verify_path": str(verify_path),
        "preview_path": str(preview) if rendered else None,
    }


def main(argv=None):
    argv = argv or sys.argv[1:]
    if len(argv) < 4:
        print(
            "Usage: verify_pack.py <pack_dir> <resume.pdf> <letter.pdf> <job_title> [jd...]",
            file=sys.stderr,
        )
        return 2
    pack_dir = Path(argv[0])
    resume = Path(argv[1])
    letter = Path(argv[2])
    job_title = argv[3]
    jd = " ".join(argv[4:]) if len(argv) > 4 else job_title
    result = verify_pack(pack_dir=pack_dir, resume=resume, letter=letter, job_title=job_title, jd=jd)
    print(json.dumps({k: result[k] for k in ("ok", "fails", "verify_path", "preview_path")}, indent=2))
    print(Path(result["verify_path"]).read_text(encoding="utf-8"))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
