# jobpack

**Verified-listing → tailored application pack → hard-gated send, run by any AI coding agent.**

Born from a real job hunt: every day the pipeline turns job postings into verified, tailored
application packs (resume + cover letter PDFs), and nothing is ever emailed until the human
types `send <company>`. The anti-hallucination gates exist because this author's agent once
generated a "finished" CV with stacked fonts and wrong links — and text-only checks let it
through. The visual render + verify + reviewer chain is the fix, and it is the product.

## What's in the box

```
.agents/skills/job-apply/SKILL.md   ← the agent contract: drop this into any agent
scripts/
  verify_pack.py      post-generate hard gate: PDF text extract + preview.png + PASS/FAIL sheet
  reviewer.py         HR/ATS reviewer: track classification + global + track rules → CLEAR/BLOCK SEND
  match_role.py       JD → base-CV-track classifier (never guesses unknown roles; asks the user)
  send_email.py       deep-locked sender: dry-run, SEND_DISABLED marker, filename gate, ledger
  list_sendable.py    defines exactly what "send all" may include
  audit_all_pdfs.py   sweep every pack for track confusion and dash/phrase hygiene
  userconfig.py       your identity + links from profile/user.json (gitignored)
  pdf_letter.py       gold-shape cover letter writer (Times, plain, no AI smells)
  docx_to_pdf.py      DOCX → PDF via mammoth + Chrome with layout restoration
  retitle_pdf.py      swap the CV header title without rebuilding the CV
  tailor_docx.py      edit wording inside a DOCX without touching fonts/layout
  copy_preview.py     export a pack to your preview folder
  log_apply.py        append-only event log (logs/apply.jsonl)
  learn.py            folds apply.jsonl corrections into profile/learned.json rules
templates/            cover_letter_gold.txt - the letter shape with its hard rules
profile/              user.example.json (copy → user.json), learned.example.json
docs/                 SEND_SAFETY.md, VERIFICATION.md
applications/         your generated packs (gitignored - never shared)
```

## Quickstart

```bash
pip install -r requirements.txt          # pymupdf, reportlab, python-docx, mammoth
sudo apt-get install -y poppler-utils    # pdftotext / pdfinfo used by the gates

cp profile/user.example.json profile/user.json   # fill YOUR data - gitignored
cp profile/learned.example.json profile/learned.json
mkdir -p base-cvs/software-engineer && cp your_master_cv.pdf base-cvs/software-engineer/cv.pdf
mkdir -p applications/2026-10-23_DemoRole
python scripts/verify_pack.py applications/2026-10-23_DemoRole \
  base-cvs/software-engineer/cv.pdf \
  applications/2026-10-23_DemoRole/Your_Name_DemoRole_Cover_Letter.pdf \
  "Demo Role" "Demo JD text"
```

Gmail sending (optional): `cp .env.gmail.example .env.gmail` with a Google **app password**.
`profile/SEND_DISABLED` ships ON; the agent removes it only when you typed `send <company>`.

## How your AI agent uses it

The whole method lives in one file: **`.agents/skills/job-apply/SKILL.md`**. Point any coding
agent at this repo (Claude Code, Cursor, Codex, Freebuff, ...) - the skill loads and your agent
follows the locked workflow: verify the listing → decision brief → `go <company>` → PDFs with
visual verification → `send <company>`.

Install as a reusable skill:

```bash
npx skills add <github-owner>/jobpack
```

Contributors and users never edit the skill logic; they edit `profile/user.json`,
`profile/facts.json` (gitignored), their base CVs, and - via pull requests - the gates.

## The core idea: gates, not vibes

1. **Verification of the listing** before any work (aggregators lie; the pipeline records it).
2. **verify_pack.py** - every generated PDF is text-extracted and *rendered to an image* the agent must actually look at. No CLEAR TO SEND without it.
3. **reviewer.py** - classifies the JD, then walks global rules (gold letter shape, no
   gap-sentences, no AI-sounding phrases, filename gate) and track rules (an ICT pack must not
   carry SWE links; a marketing pack must not carry dev stack).
4. **send_email.py** - dry-run default, double lock (`SEND_DISABLED` + `--i-confirm-send`),
   already-sent memory, and a full append-only ledger. "Send all" has a definition, and it excludes
   anything the gates did not bless.
5. **learn.py** - every user correction becomes a permanent rule in `learned.json`, and the
   agent reads it before the next JD. Your corrections compound.

## Privacy model

Your real identity, CVs, applicants' packs, learned rules with personal details, and send
history are all **gitignored**. The published repo ships a fictional example
(`profile/user.example.json`) and empty templates. `scripts/audit_all_pdfs.py` fails the sweep
if generic names (`cv.pdf`) sneak back in. Before you push anywhere, run:

```bash
git grep -ie "$(jq -r .email profile/user.json)"        # nothing from your config
git ls-files applications/ profile/                     # nothing personal tracked
```

## Contributing

The highest-value contributions are, in order: (1) new reviewer/verify checks - each one
originated from a real failure, so bring the failure story; (2) portal fill-sheet adapters
(SmartRecruiters, Greenhouse, Workday, Taleo...); (3) gate regression tests with redacted
JD/PDF fixtures. See `CONTRIBUTING.md`.

## Roadmap

- Regression tests with redacted fixture packs
- `websearch`-free listing adapter + `missed.py` watcher for scan-jobs runs
- Example base CVS with fictional persons for all tracks
- Portal autofill helpers beyond fill-sheets

## License

MIT - see [LICENSE](LICENSE).
