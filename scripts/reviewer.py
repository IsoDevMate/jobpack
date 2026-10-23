# -*- coding: utf-8 -*-
"""Global HR/ATS reviewer for resume PDF + cover letter PDF.

The reviewer classifies the JD (pick_base), runs every PDF through the verify
gate, then walks global letter rules + track rules. Personal asset checks
(specific employers, named pages) are config-driven: add them under
`track_rules` in profile/user.json, or contribute generic ones to the repo.
"""

from pathlib import Path
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from match_role import pick_base  # noqa: E402
from log_apply import log_event  # noqa: E402
from userconfig import load as load_user  # noqa: E402

FACTS = {}
FACTS_PATH = ROOT / "profile" / "facts.json"  # optional, gitignored
if FACTS_PATH.exists():
    FACTS = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
LEARNED_PATH = ROOT / "profile" / "learned.json"
LEARNED = (
    json.loads(LEARNED_PATH.read_text(encoding="utf-8"))
    if LEARNED_PATH.exists()
    else {"never_again": []}
)
USER = load_user()
PREFIX = USER["filename_prefix"].replace(" ", "_")


def pdf_text(path: Path) -> str:
    r = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True)
    return (r.stdout or "").lower()


def pdf_text_raw(path: Path) -> str:
    r = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True)
    return r.stdout or ""


def letter_source_text(letter: Path) -> str:
    # Prefer PDF bytes (source of truth). Only use sibling .txt if it is the letter draft,
    # never email-draft.txt (that file often has STATUS m-dashes and would false-fail C9).
    txt = letter.with_suffix(".txt")
    if txt.exists() and "cover_letter" in txt.name.lower().replace("-", "_"):
        return txt.read_text(encoding="utf-8")
    return pdf_text_raw(letter)


def check(name, ok, detail):
    return {"name": name, "result": "PASS" if ok else "FAIL", "detail": detail}


def review_pack(*, job_title: str, company: str, jd: str, resume: Path, letter: Path, go_approved: bool):
    from verify_pack import verify_pack  # local hard gate

    resume, letter = Path(resume), Path(letter)
    pack_dir = resume.parent
    verify = verify_pack(pack_dir=pack_dir, resume=resume, letter=letter, job_title=job_title, jd=jd)

    rt = pdf_text(resume)
    lt = pdf_text(letter)
    blob = f"{job_title}\n{jd}".lower()
    match = pick_base(job_title, jd)
    folder = match.get("folder")
    is_marketing = folder == "marketing"
    is_swe = folder in {"software-engineer", "java-developer", "backend-developer"}

    checks = []
    # Hard gate first: PDF extract + preview.png must pass or verdict cannot be CLEAR
    checks.append(
        check(
            "V0 VERIFY.txt + preview.png passed",
            verify["ok"],
            f"fails={verify['fails']}; see {verify['verify_path']}",
        )
    )
    checks.append(check("M1 folder vs JD", folder is not None, f"pick_base -> {match}"))
    checks.append(
        check(
            "M2 teaching CV not used for engineer JD",
            not (folder == "coding-teacher" and any(w in blob for w in ("engineer", "developer", "qa", "senior"))),
            "coding-teacher forbidden on SWE/senior",
        )
    )
    # Education honesty (generic): if facts declare education, the CV must carry it.
    edu = " ".join(str(FACTS.get("education", "")).lower().split()) or ""
    if edu:
        edu_words = [w for w in re.split(r"[\s,]+", edu) if len(w) > 4]
        checks.append(
            check(
                "E1 CV carries the declared education",
                all(w in rt for w in edu_words[:4]) if edu_words else True,
                f"facts declare: {edu}",
            )
        )

    # Cover letter (global)
    checks.append(check("C1 Yours sincerely", "yours sincerely" in lt, "Gold close"))
    checks.append(
        check(
            "C2 no gap sentences",
            "i do not" not in lt and "i don't have" not in lt and "not a career" not in lt and "i have not added" not in lt,
            "Never advertise missing tools",
        )
    )
    checks.append(check("C3 job title in letter", job_title.lower() in lt, job_title))
    checks.append(check("C4 company in letter", company.lower() in lt, company))
    checks.append(check("C5 thank you", "thank you" in lt, "Gold close"))
    if is_marketing:
        checks.append(
            check(
                "C6 marketing letter has no dev-stack names",
                "nestjs" not in lt and "kubernetes" not in lt and "spring boot" not in lt,
                "Dev stack does not belong on a marketing letter",
            )
        )
        header = rt.split("experience", 1)[0]
        checks.append(
            check(
                "R6 marketing header has no LinkedIn profile",
                "linkedin.com" not in header and not header.strip().endswith("linkedin"),
                "A dev-profile LinkedIn does not belong on a marketing header",
            )
        )
        # Config-named social pages: if named_employers is set, the CV must carry them
        named = [e.lower() for e in USER.get("named_employers") or []]
        if named:
            checks.append(
                check(
                    "R7 named pages appear on the CV",
                    all(e in rt for e in named),
                    f"config named_employers: {named}",
                )
            )
            checks.append(
                check(
                    "C7 letter names the pages on the CV",
                    all(e.split()[0] in lt for e in named if e.split()),
                    "Cover letter should mention the same pages the CV does",
                )
            )

    if is_swe:
        checks.append(
            check(
                "R5 SWE CV is not a teaching/mentor heading",
                "coding & robotics" not in rt and "mental health facilitator" not in rt,
                "Wrong master",
            )
        )
        recent = str(USER.get("recent_year") or "")
        if any(x in blob for x in ("software", "full stack", "fullstack", "developer", "engineer", "system developer")):
            checks.append(
                check(
                    "L4 resume includes a recent role",
                    (recent in rt) if recent else ("present" in rt),
                    "Do not ship a master that stops before your most recent work",
                )
            )

        # ICT / support / technician packs: no SWE social header; no DevOps-led CV
        ictish = any(
            x in blob
            for x in (
                "ict technician",
                "ict intern",
                "digital workplace",
                "it officer",
                "hardware support",
                "help desk",
                "helpdesk",
                "desktop support",
                "ict & data",
                "ict and data",
                "data officer",
                "ict data",
                "information systems assistant",
                "it manager",
                "ict attachment",
                "ict clerk",
            )
        )
        if ictish:
            header = rt.split("experience", 1)[0]
            checks.append(
                check(
                    "L6 ICT/support header has no LinkedIn/GitHub/Portfolio",
                    "linkedin" not in header and "github" not in header and "portfolio" not in header,
                    "Those links are for software roles only",
                )
            )
            checks.append(
                check(
                    "L7 ICT resume is not DevOps/SWE-led",
                    "kubernetes" not in rt
                    and "terraform" not in rt
                    and "openai" not in rt
                    and "backend & devops" not in rt
                    and "nestjs" not in rt,
                    "ICT pack must lead support work, not K8s/AI/SaaS bullets",
                )
            )
            checks.append(
                check(
                    "L8 ICT resume names support work",
                    "first-level" in rt or "first-line" in rt or "ict" in rt or "help desk" in rt,
                    "Must show real ICT/support experience on the CV",
                )
            )

    # Cover letters: avoid the formulaic AI pattern
    checks.append(
        check(
            "C8 no formulaic 'Your role asks / That matches' letter",
            "your role asks" not in lt and "that matches" not in lt,
            "Gold letter: interest + real employers + JD reason to hire - not template matching lines",
        )
    )
    letter_raw = letter_source_text(letter)
    checks.append(
        check(
            "C9 no em/en dashes in cover letter",
            "\u2014" not in letter_raw and "\u2013" not in letter_raw,
            "Never use m-dash or en-dash in letters; ASCII hyphen only",
        )
    )
    checks.append(
        check(
            "C10 no 'I want this role because'",
            "i want this role because" not in lt,
            "Gold letter: I am interested in this role because... / I am especially interested...",
        )
    )
    # Soft AI voice tells
    stacked = lt.count("i work with") + lt.count("i have experience") + lt.count("i have worked")
    checks.append(
        check(
            "C11 limited 'I work with / I have experience' stacking",
            stacked <= 2,
            f"count={stacked}; prefer ownership sentences over tool laundry lists",
        )
    )

    checks.append(
        check(
            "F1 PDF filenames",
            resume.name.startswith(PREFIX) and resume.suffix == ".pdf" and "Resume" in resume.name,
            resume.name,
        )
    )
    checks.append(check("F2 letter is PDF", letter.suffix == ".pdf" and "Cover_Letter" in letter.name, letter.name))
    header = rt.split("experience", 1)[0]
    checks.append(
        check(
            "L1 no professional summary unless cloud-architect JD",
            "professional summary" not in rt
            or any(x in blob for x in ("cloud engineer", "cloud architect", "solutions architect")),
            "Use an experience-first master, not a summary-first one",
        )
    )
    title_ok = job_title.lower() in header or job_title.lower() in rt[:500]
    leftover_generic = any(
        x in header and x not in job_title.lower()
        for x in ("software engineer", "cloud engineer", "marketing professional")
    )
    checks.append(
        check(
            "L2 header title is this JD title",
            title_ok and not leftover_generic,
            f"Header must say {job_title}, not the master's own label",
        )
    )

    checks.append(check("P1 user said go", go_approved, "Do not send until go + send"))

    fails = [c for c in checks if c["result"] == "FAIL"]
    return {
        "pack": f"{company} — {job_title}",
        "track": folder,
        "verdict": "BLOCK SEND" if fails else "CLEAR TO SEND",
        "fail_count": len(fails),
        "checks": checks,
        "certs_advice": certs_for_track(folder),
        "learned_rules_loaded": len(LEARNED.get("never_again") or []),
    }


def certs_for_track(folder: str) -> str:
    if folder == "marketing":
        return (
            "Marketing/social JD: attach CV + cover letter only. "
            "Do not attach cloud/dev PDFs - those read as a developer."
        )
    if folder in {"software-engineer", "java-developer", "cloud-engineer"}:
        return (
            "Attach certificates only when the JD asks for them."
        )
    if folder == "coding-teacher":
        return "Degree certificate + teaching credential if they ask."
    return "Only attach certs the JD asks for. Default: CV + cover letter."


def to_md(report: dict) -> str:
    lines = [
        f"# REVIEWER — {report['pack']}",
        "",
        f"**Track:** `{report['track']}`",
        f"**Verdict: {report['verdict']}** ({report['fail_count']} failed)",
        f"Loaded {report['learned_rules_loaded']} learned guards from profile/learned.json",
        "",
        "## Certificates",
        report["certs_advice"],
        "",
        "| Guard | Result | Detail |",
        "|---|---|---|",
    ]
    for c in report["checks"]:
        lines.append(f"| {c['name']} | {c['result']} | {c['detail']} |")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) != 6:
        print(
            "Usage: reviewer.py <resume.pdf> <letter.pdf> <job_title> <company> <jd file or one-line jd>",
            file=sys.stderr,
        )
        print("Writes REVIEWER.md next to the resume and prints the report.", file=sys.stderr)
        raise SystemExit(2)
    resume = Path(sys.argv[1])
    letter = Path(sys.argv[2])
    job_title, company = sys.argv[3], sys.argv[4]
    jd_arg = Path(sys.argv[5])
    jd = jd_arg.read_text(encoding="utf-8") if jd_arg.exists() else sys.argv[5]
    report = review_pack(
        job_title=job_title,
        company=company,
        jd=jd,
        resume=resume,
        letter=letter,
        go_approved=False,
    )
    md = to_md(report)
    dest = resume.parent / "REVIEWER.md"
    dest.write_text(md, encoding="utf-8")
    print(md)
