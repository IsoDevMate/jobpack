# -*- coding: utf-8 -*-
"""Fold logs/apply.jsonl into profile/learned.json after every rank or correction."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "logs" / "apply.jsonl"
LEARNED = ROOT / "profile" / "learned.json"


def fold():
    learned = {"updated_from": "logs/apply.jsonl", "never_again": [], "after_every_rank": []}
    if LEARNED.exists():
        learned = json.loads(LEARNED.read_text(encoding="utf-8"))
    never = list(learned.get("never_again") or [])
    seen = set(never)
    if LOG.exists():
        for line in LOG.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            fix = row.get("fix")
            if fix and fix not in seen:
                never.append(fix)
                seen.add(fix)
    learned["never_again"] = never
    learned.setdefault(
        "after_every_rank",
        [
            "Append to logs/apply.jsonl",
            "Re-run scripts/learn.py",
            "New user facts go in profile/facts.json",
        ],
    )
    LEARNED.write_text(json.dumps(learned, indent=2), encoding="utf-8")
    return learned


if __name__ == "__main__":
    data = fold()
    print(f"learned.json now has {len(data['never_again'])} rules")
