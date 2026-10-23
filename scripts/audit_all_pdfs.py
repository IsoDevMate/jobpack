# -*- coding: utf-8 -*-
"""Audit every resume/letter PDF in applications/. Exit 1 if any ICT/support pack is dirty.

Generic checks only: track confusion, banned phrases, dash hygiene, and the
attachment-name gate. Personal employer-content rules live in the reviewer's
per-user learned rules, not here.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from userconfig import prefix  # noqa: E402

APPS = ROOT / "applications"

SWE_LINKS = ("linkedin.com", "github.com", "linkedin |", "github |", "portfolio")
ICT_NOISE = (
    "kubernetes",
    "terraform",
    "nestjs",
    "co-founder",
    "co founder",
    "founding engineer",
    "backend & devops",
)
ICT_NAME = ("ict", "itofficer", "it_officer", "hardware", "technician", "supportintern", "dataofficer", "trainer")


def pdf_text(path: Path) -> str:
    r = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True)
    return r.stdout or ""


def is_ict_pack(name: str) -> bool:
    n = name.lower().replace("-", "").replace("_", "")
    return any(h.replace("_", "") in n for h in ICT_NAME) or "ict" in name.lower()


def main() -> int:
    pre = prefix()
    fails = []
    rows = []
    for pack in sorted(APPS.iterdir()):
        if not pack.is_dir():
            continue
        resumes = list(pack.glob(f"{pre}_*_Resume.pdf")) + list(pack.glob("cv.pdf"))
        letters = list(pack.glob(f"{pre}_*_Cover_Letter.pdf")) + list(pack.glob("cover-letter.pdf"))
        if not resumes and not letters:
            continue
        ict = is_ict_pack(pack.name)
        issues = []
        for pdf in resumes:
            t = pdf_text(pdf).lower()
            if ict:
                header = t.split("experience", 1)[0]
                for s in SWE_LINKS:
                    if s in header:
                        issues.append(f"resume SWE_LINK:{s}")
                for s in ICT_NOISE:
                    if s in t:
                        issues.append(f"resume NOISE:{s}")
                evidence_words = ("first-line", "first-level", "support", "help desk", "helpdesk")
                if not any(s in t for s in evidence_words):
                    issues.append("resume shows no first-line/support evidence")
        for pdf in letters:
            t = pdf_text(pdf)
            tl = t.lower()
            if "i want this role because" in tl:
                issues.append("letter BANNED_WANT")
            if "\u2014" in t or "\u2013" in t:
                issues.append("letter MDASH")
            if "your role asks" in tl or "that matches" in tl:
                issues.append("letter FORMULA")
        apply = pack / "APPLY.txt"
        status = apply.read_text(encoding="utf-8", errors="ignore").splitlines()[0] if apply.exists() else "no-APPLY"
        rows.append((pack.name, ict, issues, status))
        if issues:
            fails.append((pack.name, issues))

    print(f"{'PACK':55} STATUS")
    for name, ict, issues, status in rows:
        mark = "FAIL" if issues else "OK  "
        print(f"{mark} {name[:53]:53} ict={ict} | {status[:50]}")
        for i in issues:
            print(f"     - {i}")
    print(f"\npacks={len(rows)} fails={len(fails)}")
    print("SEND lock:", "ON" if (ROOT / "profile" / "SEND_DISABLED").exists() else "OFF (dangerous)")
    ledger = ROOT / "logs" / "send_ledger.jsonl"
    if ledger.exists():
        sent = sum(1 for line in ledger.read_text().splitlines() if '"event": "sent"' in line or '"event":"sent"' in line)
        print(f"send_ledger sent events: {sent}")
    else:
        print("send_ledger: none yet (no tool sends recorded)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
