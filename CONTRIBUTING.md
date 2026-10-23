# Contributing to jobpack

Thanks for helping make agent-generated job applications trustworthy. The repo's value is its
gates - every check here stopped a real mistake from reaching a real employer.

## Good first contributions

### 1. New reviewer/verify checks (highest value)

Each check must originate from a real failure you observed (yours or a linked issue). Open the
PR with:

- the failure story (one paragraph, screenshots welcome)
- the check implementation in `scripts/verify_pack.py` (V-series) or `scripts/reviewer.py`
  (C/R/L/M series), with the track scoping applied where relevant
- a regression test fixture under `tests/` (see below)

A check that cannot explain how to *fix* the failure in one line is not accepted.

### 2. Portal fill-sheet adapters

SmartRecruiters, Greenhouse, Workday, Taleo, and friends each have quirks (email confirmation
fields, phone format magic, file size caps, autofill-from-resume behaviors). Add:
`docs/portals/<portal>.md` with the field map, the fill sheet template, and warnings. The
method never changes: pack → fill sheet → human uploads. Portals are never emailed.

### 3. Gate regression tests

The repo currently ships without tests - help fix that first. Useful fixtures:

- a minimal fictional resume PDF + letter PDF (generate with the shipped scripts; no real names)
- table tests over `match_role.pick_base` (JD text in → folder out, including the traps:
  graduate trainee, IT manager, enumerator with the word "data", marketing with the word "brand")
- `send_email.validate_attachments` cases: proper names pass, `cv.pdf` blocked, combined
  single-document pass, missing letter blocked

Run: `python -m pytest tests/` (keep tests dependent-free beyond requirements.txt)

### 4. Rules and templates

Learned rules live per-user in `profile/learned.json` (gitignored). Generic rules that helped
you belong in `templates/` or as gate checks with a fixture. Do not PR a profile containing
your real name, employers, or links - that is what `profile/user.example.json` is for, kept
fictional.

## Ground rules

- Keep the locks: dry-run default, SEND_DISABLED, VERIFICATION + VERIFY gates, filename gate.
- No new Python dependencies without discussion; the gates must stay pip-installable small.
- Python style: stdlib first, functions under ~60 lines, comments say *why*.
- Commits: imperative subject, one concern per commit.

## Reporting a bug

Open an issue with: what you asked the agent for, what it produced (redacted), which gate
should have caught it, and the pack's `VERIFY.txt` / `REVIEWER.md` if present.
