#!/usr/bin/env python3
"""Send a prepared application email - HARD LOCKED by default.

Safety:
  1. Dry-run unless --confirm AND --i-confirm-send
  2. Blocked while profile/SEND_DISABLED exists (default ON)
  3. Refuses if APPLY.txt / email-draft already marked SENT (unless --force-resend)
  4. **Attachment filename gate (CRITICAL):** only <Prefix>_*_Resume.pdf and
     <Prefix>_*_Cover_Letter.pdf (prefix from profile/user.json).
     Never cv.pdf / cv.docx / cover-letter.pdf.
  5. Preflight: VERIFY.txt must say VERIFY PASS when present
  6. Appends every attempt to logs/send_ledger.jsonl
  7. Never auto-sends. "send all" = only packs with APPLY NOT SENT + proper names.

Setup (once, local only - never commit):
  cp .env.gmail.example .env.gmail
"""

from __future__ import annotations

import argparse
import json
import re
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys_path = str(ROOT / "scripts")
if sys_path not in __import__("sys").path:
    __import__("sys").path.insert(0, sys_path)

from userconfig import combined_re, letter_re, resume_re  # noqa: E402

SEND_DISABLED = ROOT / "profile" / "SEND_DISABLED"
LEDGER = ROOT / "logs" / "send_ledger.jsonl"

FORBIDDEN_ATTACH = {
    "cv.pdf",
    "cv.docx",
    "cover-letter.pdf",
    "cover_letter.pdf",
    "coverletter.pdf",
    "resume.pdf",
    "letter.pdf",
}
RESUME_RE = resume_re()
LETTER_RE = letter_re()
# Some employers mandate CV + cover letter (+ ID) as ONE combined document.
COMBINED_RE = combined_re()
PREFIX = RESUME_RE.pattern.split("_")[0].lstrip("^")


def load_env():
    path = ROOT / ".env.gmail"
    if not path.exists():
        raise SystemExit(
            "No .env.gmail found. Copy .env.gmail.example, add a Gmail APP PASSWORD "
            "(Google Account -> Security -> 2-Step Verification -> App passwords). "
            "Do not use your normal Gmail password. Do not put passwords in chat."
        )
    data = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data


def parse_draft(text: str):
    meta = {}
    body_lines = []
    in_body = False
    for line in text.splitlines():
        if line.startswith("BODY:"):
            in_body = True
            continue
        if in_body:
            if line.startswith("---"):
                break
            body_lines.append(line)
            continue
        if line.startswith("TO:"):
            meta["to"] = line.split(":", 1)[1].strip()
        elif line.startswith("SUBJECT:"):
            meta["subject"] = line.split(":", 1)[1].strip()
        elif line.startswith("ATTACH:"):
            meta["attach"] = [a.strip() for a in line.split(":", 1)[1].split(",") if a.strip()]
    meta["body"] = "\n".join(body_lines).strip()
    if "[ADD YOUR SALARY EXPECTATION]" in meta.get("subject", ""):
        raise SystemExit("Subject still has [ADD YOUR SALARY EXPECTATION]. Edit email-draft.txt first.")
    return meta


def already_sent(folder: Path) -> str | None:
    for name in ("APPLY.txt", "email-draft.txt", "SEND_STATUS.txt"):
        p = folder / name
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        head = "\n".join(text.splitlines()[:8]).upper()
        if "ALREADY SENT" in head or "STATUS: SENT" in head or head.startswith("SENT"):
            return f"{name} marks this pack as already sent"
        if "SENT_WITH_BAD" in head:
            return f"{name} marks this pack as already sent (bad filenames)"
    return None


def validate_attachments(names: list[str]) -> None:
    if len(names) == 1 and COMBINED_RE.match(names[0]):
        return  # single combined document is an employer-mandated exception
    if not names or len(names) < 2:
        raise SystemExit(
            "BLOCKED: need at least Resume + Cover_Letter attachments. "
            "Got: " + repr(names)
        )
    bad = []
    for name in names:
        low = name.lower()
        if low in FORBIDDEN_ATTACH or low.startswith("cv.") or low in {
            "cover-letter.pdf",
            "cover_letter.pdf",
        }:
            bad.append(f"{name} (forbidden generic name)")
            continue
        if not (
            RESUME_RE.match(name) or LETTER_RE.match(name) or COMBINED_RE.match(name)
        ):
            bad.append(
                f"{name} (must be {PREFIX}_<Role>_Resume.pdf, "
                f"..._Cover_Letter.pdf, or ..._Combined.pdf)"
            )
    if bad:
        raise SystemExit(
            "BLOCKED: attachment filename gate failed:\n  - "
            + "\n  - ".join(bad)
            + "\nRename files + update email-draft ATTACH before send. Never ship cv.pdf."
        )
    resumes = [n for n in names if RESUME_RE.match(n)]
    letters = [n for n in names if LETTER_RE.match(n)]
    if not resumes:
        raise SystemExit(f"BLOCKED: no {PREFIX}_*_Resume.pdf in ATTACH")
    if not letters:
        raise SystemExit(f"BLOCKED: no {PREFIX}_*_Cover_Letter.pdf in ATTACH")


def listing_verification_gate(folder: Path) -> None:
    """Block document-ready packs whose job listing/channel is not verified open."""
    for name in ("email-draft.txt", "APPLY.txt"):
        path = folder / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.upper().startswith("VERIFICATION:"):
                status = line.split(":", 1)[1].strip().upper()
                if status == "VERIFIED_OPEN":
                    return
                raise SystemExit(f"BLOCKED: listing verification status is {status}, not VERIFIED_OPEN.")
    raise SystemExit("BLOCKED: no explicit VERIFICATION: VERIFIED_OPEN status in the pack.")


def verify_gate(folder: Path) -> None:
    verify = folder / "VERIFY.txt"
    if not verify.exists():
        raise SystemExit(
            "BLOCKED: no VERIFY.txt. Run verify_pack.py and Read preview.png before send. "
            "Do not assume the pack is ready."
        )
    text = verify.read_text(encoding="utf-8", errors="ignore")
    if "Verdict: VERIFY PASS" not in text and "VERIFY PASS" not in text:
        raise SystemExit("BLOCKED: VERIFY.txt is not PASS. Fix the pack, re-verify, then send.")


def ledger(event: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    event = {"ts": datetime.now(timezone.utc).isoformat(), **event}
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--app", required=True, help="Folder name under applications/")
    p.add_argument("--confirm", action="store_true", help="Required with --i-confirm-send to send.")
    p.add_argument(
        "--i-confirm-send",
        action="store_true",
        help="Second lock. Must match user chat command send <company>.",
    )
    p.add_argument(
        "--force-resend",
        action="store_true",
        help="Override ALREADY SENT markers. Rare. User must ask explicitly.",
    )
    p.add_argument(
        "--skip-verify",
        action="store_true",
        help="Dangerous. Only if user explicitly allows sending without VERIFY.txt.",
    )
    args = p.parse_args()
    folder = ROOT / "applications" / args.app
    draft_path = folder / "email-draft.txt"
    if not draft_path.exists():
        raise SystemExit(f"No email-draft.txt in {folder}")
    raw = draft_path.read_text(encoding="utf-8", errors="ignore")
    if "PORTAL APPLICATION" in raw or "YOU MUST UPLOAD ON THE PORTAL" in raw:
        raise SystemExit(
            "This role is a careers portal / form, not email. Upload the PDFs yourself."
        )
    meta = parse_draft(raw)
    attach = meta.get("attach") or []
    print("TO:", meta.get("to"))
    print("SUBJECT:", meta.get("subject"))
    print("ATTACH:", attach)
    print("BODY:\n", meta.get("body"))

    # Always validate filenames - even on dry-run - so mistakes surface early
    try:
        validate_attachments(attach)
        for name in attach:
            if not (folder / name).exists():
                raise SystemExit(f"Missing attachment file: {folder / name}")
        listing_verification_gate(folder)
        if not args.skip_verify:
            verify_gate(folder)
        print("PREFLIGHT: listing VERIFIED_OPEN; attachment names OK; VERIFY OK")
    except SystemExit as e:
        ledger(
            {
                "event": "blocked_preflight",
                "app": args.app,
                "reason": str(e),
                "attach": attach,
            }
        )
        raise

    will_send = bool(args.confirm and args.i_confirm_send)
    if not will_send:
        ledger({"event": "dry_run", "app": args.app, "to": meta.get("to"), "attach": attach})
        print("\nDry run only. Nothing was sent.")
        print("To actually send (after user typed send <company>):")
        print("  1) remove profile/SEND_DISABLED")
        print("  2) re-run with --confirm --i-confirm-send")
        return

    if SEND_DISABLED.exists():
        ledger({"event": "blocked_send_disabled", "app": args.app})
        raise SystemExit(
            "BLOCKED: profile/SEND_DISABLED is present. "
            "Agent must not remove this unless the user typed send <company>. "
            "Nothing was sent."
        )

    reason = already_sent(folder)
    if reason and not args.force_resend:
        ledger({"event": "blocked_already_sent", "app": args.app, "reason": reason})
        raise SystemExit(f"BLOCKED: {reason}. Use --force-resend only if the user asked to resend.")

    env = load_env()
    user = env["GMAIL_ADDRESS"]
    password = env["GMAIL_APP_PASSWORD"]
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = meta["to"]
    msg["Subject"] = meta["subject"]
    msg.set_content(meta["body"])
    for name in attach:
        f = folder / name
        data = f.read_bytes()
        subtype = "pdf" if f.suffix.lower() == ".pdf" else "octet-stream"
        msg.add_attachment(
            data,
            maintype="application",
            subtype=subtype,
            filename=f.name,
        )
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (folder / "SEND_STATUS.txt").write_text(
        f"SENT {stamp}\nTO: {meta.get('to')}\nSUBJECT: {meta.get('subject')}\nATTACH: {', '.join(attach)}\n",
        encoding="utf-8",
    )
    apply = folder / "APPLY.txt"
    if apply.exists():
        apply.write_text(
            f"SENT {stamp}. Do not send again.\n\n" + apply.read_text(encoding="utf-8", errors="ignore"),
            encoding="utf-8",
        )
    ledger(
        {
            "event": "sent",
            "app": args.app,
            "to": meta.get("to"),
            "subject": meta.get("subject"),
            "attach": attach,
        }
    )
    print("Sent. Recorded in logs/send_ledger.jsonl and SEND_STATUS.txt.")


if __name__ == "__main__":
    main()
