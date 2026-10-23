# -*- coding: utf-8 -*-
"""Refresh <preview_dir>/00_PENDING.txt from opportunities/pipeline.json."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from userconfig import preview_dir  # noqa: E402

PIPE = json.loads((ROOT / "opportunities" / "pipeline.json").read_text(encoding="utf-8"))


def main():
    DEST = preview_dir() / "00_PENDING.txt"
    DEST.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "PENDING - jobs not sent yet",
        "Open this file any time. Nothing here has been emailed.",
        "After you like the PDFs in the matching folder, type in chat: send <company>",
        "",
        "=== RANKED - TYPE go <company> FOR PDFs ===",
        "",
    ]
    awaiting = PIPE.get("awaiting_go") or []
    if not awaiting:
        lines.append("(none)")
    for row in awaiting:
        lines += [
            f"* {row['company']} — {row['role']}  [{row.get('verdict', 'awaiting')}]",
            f"  Deadline: {row.get('deadline') or '?'}",
            f"  How: {row.get('how', '')}",
            f"  Pack: applications/{row.get('pack', '')}",
            f"  {row.get('note', '')}",
            "",
        ]
    lines += ["=== SHORT SET (verify then apply) ===", ""]
    shortset = PIPE.get("shortset") or []
    if not shortset:
        lines += ["(none)", ""]
    for row in shortset:
        lines += [
            f"* {row['company']} — {row['role']}  [{row.get('verification', 'UNVERIFIED')}]",
            f"  Verdict: {row.get('verdict', 'VERIFY_FIRST')}",
            f"  How: {row.get('how', '')}",
            f"  Pack: applications/{row.get('pack', '')}",
            f"  {row.get('note', '')}",
            "",
        ]
    lines += ["=== READY - SEND IF YOU WANT THEM (PDFs ready) ===", ""]
    ready = PIPE.get("ready_not_sent") or []
    if not ready:
        lines.append("(none)")
        lines.append("")
    for row in ready:
        lines += [
            f"* {row['company']} — {row['role']}",
            f"  Deadline: {row.get('deadline', '?')}",
            f"  How: {row.get('how', '')}",
            f"  Folder: applications/{row.get('pack', '')}",
            "",
        ]
    lines += ["=== ALREADY SENT (do not follow up) ==="]
    for row in PIPE.get("sent") or []:
        lines.append(f"* {row['company']} — {row['role']} ({row['date']})")
    DEST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(DEST)


if __name__ == "__main__":
    main()
