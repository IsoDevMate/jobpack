---
name: job-apply
description: >-
  Tailors a CV and cover letter from a job posting screenshot, PDF, URL, or
  pasted JD. Use when the user wants to apply, uploads a job description, drops
  a posting into job-postings/, or says apply / JD / cover letter.
---

# Job Application Assistant

Not an app. Posting in → **decision brief** → user says `go <company>` → PDFs → preview folder → user types `send <company>`.

**Send is locked by default.** `profile/SEND_DISABLED` blocks `scripts/send_email.py`. Preparing PDFs never emails. See `docs/SEND_SAFETY.md`. After every ranking or user correction: append `logs/apply.jsonl`, run `scripts/learn.py` so `profile/learned.json` grows. Read `learned.json` **before** the next JD.

Corrections are the reinforcement loop: when the user tweaks wording, adds a role, or fixes a fact, log `event: correction` with `what` + `fix`, update `profile/facts.json`, then run `scripts/learn.py`. Do not silently ignore chat corrections.

**First-time setup you must walk the user through** (skip what already exists):
1. `cp profile/user.example.json profile/user.json` → fill name, email, phone, city, `filename_prefix` (e.g. `Jane_Mbugua`), links. This file is gitignored; never commit it.
2. `cp profile/learned.example.json profile/learned.json` (empty rulebook; it grows).
3. Put CV masters in `base-cvs/<track>/cv.pdf` (software-engineer, marketing...). A master is a finished, real CV you only retitle per job.
4. Optional Gmail sends: `cp .env.gmail.example .env.gmail` (app password, never your login password).

**Verify the listing before any application work.** Prefer the employer's official careers page or an authoritative host (ReliefWeb, SmartRecruiters, official portals). Aggregators and social posts are discovery sources only until traced to the original listing. Confirm: role open, deadline, location, employer-owned email or portal, requirements, submission instructions. Record one of `VERIFIED_OPEN`, `VERIFIED_CLOSED`, `PARTIALLY_VERIFIED`, `UNVERIFIED`, `SUSPICIOUS` in `opportunities/pipeline.json`. Never describe an unverified listing as ready to apply. Verification does not authorize submission: still require `go <company>` to prepare and `send <company>` to email; confirm before a portal's final Submit.

When the text below says *Read*, actually read the file or render and view the image. Do not claim to have verified something you did not inspect.

## Hard verify before CLEAR (anti-hallucination)

After every pack generate, **in order**:

1. Write `<Prefix>_<Role>_Resume.pdf` + `<Prefix>_<Role>_Cover_Letter.pdf` into the pack folder `applications/<date>_<Company>_<Role>/` (overwrite; delete old junk).
2. Run `python scripts/verify_pack.py <pack> <resume.pdf> <letter.pdf> "<title>" "<jd>"`
   - extracts PDF text → `VERIFY.txt`
   - renders resume page 1 → `preview.png`
3. **Read `preview.png`** (visual check). Read `VERIFY.txt`.
4. Run `reviewer.py <resume.pdf> <letter.pdf> "<title>" "<company>" "<jd>"` (it runs verify again; V0 fail ⇒ BLOCK SEND, never CLEAR).
5. Only then tell the user CLEAR. If VERIFY FAIL, fix the PDF and repeat - do not claim done.

This exists because text-only checks pass while the PDF still shows wrong links, stacked fonts, or a stale master. `preview.png` is the guard.

## Workflow (this is the gate)

```
- [ ] 1. Read JD (title, company, verbs, tools, seniority)
- [ ] 2. pick_base() - which base-cvs master. Stop and ask the user if unknown.
- [ ] 3. Score the job on that master vs THIS JD (lead / keep / shrink)
- [ ] 4. Write DECISION.md into the pack: why relevant, ATS hits/misses, recommended set
- [ ] 5. Copy the pack to <preview_dir> (scripts/copy_preview.py) and wait
- [ ] 6. User: go <company>  → then customize wording
- [ ] 7. PDFs → <preview_dir> → user reviews
- [ ] 8. User: send <company> → the ONLY condition that lifts profile/SEND_DISABLED
```

## Reading the base CVs

- Read `profile/facts.json` and `templates/cover_letter_gold.txt` before writing anything.
- A master carries *tracks* (for example: a product where you led marketing vs built engineering). A marketing JD uses the marketing bullets; a software JD uses the engineering bullets. Never mix the two tracks in one document.
- Retitle with `scripts/retitle_pdf.py` (header title line only). Never rebuild a master from scratch per job; tailor wording only.
- Essays of education go from `facts.json` only. Never invent a diploma, a certificate, an employer, or a date.

## Hard failures to never repeat

- Do **not** send until the user types `send <company>` in this turn.
- Do **not** remove `profile/SEND_DISABLED` or run `send_email.py --confirm --i-confirm-send` without it.
- Do **not** take or store Linux sudo / Gmail / portal passwords from chat. If the user pastes one, tell them to change it and ignore it.
- Attach only `<Prefix>_<Role>_Resume.pdf` and `<Prefix>_<Role>_Cover_Letter.pdf`. Never `cv.pdf` / `cover-letter.pdf`; `send_email.py` hard-blocks those (`list_sendable.py` defines what `send all` may include).
- Before every send: open the ATTACH line + `ls` the pack folder + Read `preview.png` / `VERIFY.txt`.
- Portal applications (`PORTAL APPLICATION` in email-draft) are never emailed; produce the fill sheet and tell the user to upload.
- Cover letters clone the gold shape: who I am + why this role, strongest work with outcomes, 1-2 real employers on the CV, why this JD fits that work, degree. Never "Your role asks for X. That matches Y." Never "I want this role because".
- Cover letters: **never** em dash (—) or en dash (–). ASCII hyphen only. Short clear sentences. Max 2 uses of "I work with / I have experience".
- Never write "I do not have X / I am not a Y" in a cover letter. Skills you lack are not mentioned; skills you have do the selling.
- Do not style CV text in ReportLab/PIL by hand; edit the DOCX master or retitle the PDF (font overlay stacking is how reported "double name" bug renders happen).
- Every missing-assumption question ("which master is right here?") goes to the user. Do not guess when the classifier returns `folder: None`.
