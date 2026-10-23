# SEND SAFETY

The pipeline can prepare documents on its own but it must never email on its own. Four
independent locks stand between a generated PDF and a real send:

1. **`profile/SEND_DISABLED` (marker file).** Present by default in a fresh clone. The agent
   removes it only after the user typed `send <company>` in the *same turn*. The audit sweep
   (`audit_all_pdfs.py`) prints whether the lock is ON or OFF.
2. **CLI double lock.** `send_email.py` requires BOTH `--confirm` and `--i-confirm-send`; a
   plain run is a dry-run that prints the full preflight (TO/SUBJECT/ATTACH/BODY) and exits.
3. **Content gates on every attempt, even dry runs.**
   - `send_email.py` refuses portal packs outright (`PORTAL APPLICATION` marker) - those are
     uploaded by the human on the employer's form.
   - listing must be explicitly `VERIFICATION: VERIFIED_OPEN` in the pack.
   - `VERIFY.txt` must say VERIFY PASS.
   - attachments must match `<Prefix>_*_Resume.pdf` / `<Prefix>_*_Cover_Letter.pdf`
     (`*_Combined.pdf` allowed only as the single attachment when an employer mandates it -
     e.g. a school board requiring CV+letter+ID in one document). Generic `cv.pdf` names are
     forbidden because they were once generated with the wrong person's contact line.
   - already-sent memory: APPLY.txt/email-draft.txt/SEND_STATUS.txt SENT markers block
     re-sending unless `--force-resend` is passed by explicit user request.
4. **The ledger.** Every attempt - dry-run, blocked, or sent - is appended to
   `logs/send_ledger.jsonl`. "Did anything go out?" is always answerable with
   `grep '"event": "sent"' logs/send_ledger.jsonl`.

## If you fear something went out silently

```bash
python scripts/audit_all_pdfs.py
tail logs/send_ledger.jsonl
```
`sent` events count 0 unless a user-commanded send happened. If your email tool shows
something you did not command, treat credentials as compromised: rotate the app password.
