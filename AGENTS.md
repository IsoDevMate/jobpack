# AGENTS.md

Rules for AI coding agents working in this repo. The full application workflow lives in
`.agents/skills/job-apply/SKILL.md`; this file covers working *on the code*.

- The send path is sacred. Changes to `send_email.py`, `list_sendable.py`, `verify_pack.py`
  must keep: dry-run default, `profile/SEND_DISABLED` gate, VERIFICATION gate, VERIFY gate,
  filename gate, append-only ledger, already-sent memory.
- All applicant identity comes from `profile/user.json` via `scripts/userconfig.py`. Never
  re-introduce hard-coded names, emails, phones, or prefixes. `profile/user.json`,
  `profile/facts.json`, `learned.json`, `applications/`, `logs/`, real masters - all gitignored.
  The repo ships only fictional examples.
- Verify behavior with the same gates you changed: run `verify_pack.py` and `reviewer.py` on a
  throwaway pack before claiming a change works.
- No Lorem-ipsum placeholders inside shipped checks. A check must say FAIL when its condition
  fails and explain how to fix it in one line.
- Python: stdlib + pymupdf/reportlab/python-docx/mammoth only. No new dependencies without
  discussion.
- Comments say why (which real failure motivated the rule); code says what.
- Every user-facing failure message starts with `BLOCKED:` or `Example:` - agent-readable.
