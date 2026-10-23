# VERIFICATION - trust the listing before any work

Aggregator posts lie about deadlines, drop application links, and sometimes invent employers.
The pipeline therefore never spends effort on unverified listings.

## Verdicts (recorded per opportunity in opportunities/pipeline.json)

| Verdict | Meaning |
|---|---|
| `VERIFIED_OPEN` | Confirmed the role is live on the employer's official channel (careers page, SmartRecruiters/Greenhouse instance, employer-owned email), with deadline + how-to-apply |
| `VERIFIED_CLOSED` | Confirmed closed/expired |
| `PARTIALLY_VERIFIED` | Employer real + channel plausible; exact link or instructions not confirmed |
| `UNVERIFIED` | Only a third-party post exists |
| `SUSPICIOUS` | Fee requests, personal-email-only contact, misspelled domains, urgency pressure |

## Sources hierarchy

1. Employer's official careers page / ATS instance (SmartRecruiters, Greenhouse, Workday...)
2. Official employer accounts posting the vacancy (their domain must match)
3. Reputable boards (ReliefWeb, LinkedIn company page) - discovery only
4. Aggregators/blog reposts/WhatsApp screenshots - never verification on their own

## The email-a-channel rule

Application email addresses are verified by cross-checking at least two independent sources
(offering page text, official social post, site footer/contact page). If no email exists and
the only path is a portal, the pack is marked portal-only and the human uploads.

`SUSPICIOUS` and any "pay to apply" signal ends the work immediately - no packs are prepared
for fee-based listings. This is also an explicit fraud line in some postings; respect it.
