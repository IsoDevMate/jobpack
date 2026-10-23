#!/usr/bin/env python3
"""List packs that are actually eligible to email.

Eligible = APPLY says NOT SENT (or no SENT marker), listing is VERIFIED_OPEN,
email-draft ATTACH uses <Prefix>_*_Resume.pdf + <Prefix>_*_Cover_Letter.pdf
(from profile/user.json), and VERIFY PASS.

"send all" / "send them all" means THIS list only - never old cv.pdf packs.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from userconfig import combined_re, letter_re, resume_re  # noqa: E402

APPS = ROOT / "applications"
FORBIDDEN = {"cv.pdf", "cv.docx", "cover-letter.pdf", "cover_letter.pdf"}


def draft_attach(folder: Path) -> list[str]:
    draft = folder / "email-draft.txt"
    if not draft.exists():
        return []
    for line in draft.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("ATTACH:"):
            return [a.strip() for a in line.split(":", 1)[1].split(",") if a.strip()]
    return []


def is_sent(folder: Path) -> bool:
    for name in ("APPLY.txt", "email-draft.txt", "SEND_STATUS.txt"):
        p = folder / name
        if not p.exists():
            continue
        head = "\n".join(p.read_text(encoding="utf-8", errors="ignore").splitlines()[:8]).upper()
        if any(x in head for x in ("ALREADY SENT", "STATUS: SENT", "SENT_WITH_BAD")) or head.startswith(
            "SENT"
        ):
            return True
    return False


def is_portal(folder: Path) -> bool:
    for name in ("APPLY.txt", "email-draft.txt"):
        p = folder / name
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8", errors="ignore").upper()
        if "PORTAL" in t or "GOOGLE FORM" in t or "YOU MUST UPLOAD" in t:
            return True
    return False


def verify_ok(folder: Path) -> bool:
    v = folder / "VERIFY.txt"
    if not v.exists():
        return False
    return "VERIFY PASS" in v.read_text(encoding="utf-8", errors="ignore")


def listing_verified_open(folder: Path) -> bool:
    """Document quality is not listing verification; require an explicit open verdict."""
    for name in ("email-draft.txt", "APPLY.txt"):
        path = folder / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.upper().startswith("VERIFICATION:"):
                return line.split(":", 1)[1].strip().upper() == "VERIFIED_OPEN"
    return False


def attach_ok(names: list[str], prefix: str) -> bool:
    RESUME_RE, LETTER_RE, COMBINED_RE = resume_re(), letter_re(), combined_re()
    if any(n.lower() in FORBIDDEN for n in names):
        return False
    if len(names) == 1 and COMBINED_RE.match(names[0]):
        return True  # employer-mandated single combined document
    if len(names) < 2:
        return False
    return any(RESUME_RE.match(n) for n in names) and any(LETTER_RE.match(n) for n in names)


def main() -> int:
    RESUME_RE, LETTER_RE, COMBINED_RE = resume_re(), letter_re(), combined_re()
    eligible = []
    blocked = []
    portals = []
    sent = []
    for folder in sorted(APPS.iterdir()):
        if not folder.is_dir():
            continue
        if not any(folder.glob("*.pdf")):
            continue
        if is_sent(folder):
            sent.append(folder.name)
            continue
        if is_portal(folder):
            portals.append(folder.name)
            continue
        attach = draft_attach(folder)
        reasons = []
        if not attach:
            reasons.append("no email-draft ATTACH")
        elif not attach_ok(attach, RESUME_RE.pattern):
            reasons.append(f"bad attach names: {attach}")
        if not verify_ok(folder):
            reasons.append("no VERIFY PASS")
        if not listing_verified_open(folder):
            reasons.append("listing is not explicitly VERIFIED_OPEN")
        if reasons:
            blocked.append((folder.name, reasons))
        else:
            eligible.append((folder.name, attach))

    print("=== ELIGIBLE TO EMAIL (this is what 'send all' means) ===")
    if not eligible:
        print("(none)")
    for name, attach in eligible:
        print(f"* {name}")
        print(f"  ATTACH: {', '.join(attach)}")

    print("\n=== PORTAL / FORM - you upload (never email) ===")
    for name in portals:
        print(f"* {name}")

    print("\n=== BLOCKED - fix before send (cv.pdf etc) ===")
    for name, reasons in blocked:
        print(f"* {name}")
        for r in reasons:
            print(f"  - {r}")

    print(f"\n=== ALREADY SENT ({len(sent)}) - do not re-send ===")
    for name in sent:
        print(f"* {name}")

    print(f"\neligible={len(eligible)} blocked={len(blocked)} portals={len(portals)} sent={len(sent)}")
    return 0  # listing always succeeds


if __name__ == "__main__":
    raise SystemExit(main())
