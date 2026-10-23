# -*- coding: utf-8 -*-
"""Pick CV folder. Domain mismatches only - not years on the JD.

Years / Manager / Head: do NOT refuse. Years come from profile/facts.json
(experience_policy) - HR lists are wish-lists; score the actual overlap.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_FACTS_PATH = ROOT / "profile" / "facts.json"  # optional, gitignored
FACTS = json.loads(_FACTS_PATH.read_text(encoding="utf-8")) if _FACTS_PATH.exists() else {}

SENIOR_JD = re.compile(r"\b(senior|lead|head|manager|principal|staff)\b", re.I)
TEACH_JD = re.compile(r"\b(teacher|trainer|facilitator|instructor|tutor|lecturer|robotics)\b", re.I)
MH_JD = re.compile(r"\b(mental health|counsel|wellbeing|psychosocial)\b", re.I)
MARKET_JD = re.compile(r"\b(marketing|social media|community manager|content creator|video editor|brand)\b", re.I)
ENUM_JD = re.compile(r"\benumerators?\b|research assistant|community research|field interview", re.I)
GRADUATE_JD = re.compile(r"\bgraduate trainee\b|\bgraduate programme\b", re.I)
SWE_JD = re.compile(
    r"\b(software|developer|engineer|full[- ]?stack|backend|frontend|java|sde|qa|test|cloud|"
    r"ict technician|ict intern|it officer|systems engineer|system developer|"
    r"information systems assistant|it manager|ict manager|head of it|"
    r"systems manager|ict.?data officer|data officer|data & analytics|ai skills)\b",
    re.I,
)
IT_SUPPORT_JD = re.compile(
    r"\b(ict technician|ict intern|ict attachment|it officer|hardware support|digital workplace|help ?desk|"
    r"desktop support|information systems assistant|it manager|ict manager|head of it|"
    r"systems manager|ict.?data|data officer)\b",
    re.I,
)


def years_stretch_note(jd_text: str) -> str:
    """Annotate DECISION only - never a refuse reason by itself."""
    policy = FACTS.get("experience_policy") or {}
    have = int(policy.get("years_in_field") or 4)
    flex = int(policy.get("flexibility_years") or 3)
    m = re.search(r"(\d+)\s*\+?\s*(?:-|to)?\s*(\d+)?\s*\+?\s*years?", jd_text.lower())
    if not m:
        return ""
    lo = int(m.group(1))
    hi = int(m.group(2) or m.group(1))
    if hi <= have + flex:
        return f"Years on JD ~{lo}-{hi}; applicant ~{have} (+-{flex}) - stretch OK, still prepare."
    return (
        f"Years on JD ~{lo}-{hi}; applicant ~{have}. Soft stretch beyond +-{flex} - "
        "still prepare if tech overlap; do not refuse on years alone."
    )


def pick_base(job_title: str, jd_text: str) -> dict:
    blob = f"{job_title}\n{jd_text}".lower()
    if MH_JD.search(blob) and not SWE_JD.search(blob):
        return {"folder": "mental-health", "reason": "JD is mental health / facilitation"}
    if TEACH_JD.search(blob) and not SENIOR_JD.search(blob) and not SWE_JD.search(blob):
        return {"folder": "coding-teacher", "reason": "JD is teaching / training / facilitating"}
    if MARKET_JD.search(blob) and not SWE_JD.search(blob) and not IT_SUPPORT_JD.search(blob):
        return {"folder": "marketing", "reason": "JD is marketing / social / video"}
    if ENUM_JD.search(blob) and not SWE_JD.search(blob):
        return {
            "folder": "data-annotation",
            "reason": "Enumerator / community research / field data collection",
            "stretch_note": years_stretch_note(jd_text),
        }
    # IT Manager / Head of IT / support: SWE track (stretch seniority is fine)
    if IT_SUPPORT_JD.search(blob):
        note = years_stretch_note(jd_text)
        return {
            "folder": "software-engineer",
            "reason": "ICT/IT support or IT manager-style role - prepare; years are soft",
            "stretch_note": note,
        }
    if GRADUATE_JD.search(blob):
        # Generalist graduate programme. The applicant's strongest angle is the
        # engineering/tech master; a generalist JD usually lists Information
        # Technology among accepted fields. Confirm with the user if unsure.
        return {
            "folder": "software-engineer",
            "reason": "Generalist graduate trainee programme - tech/AI master carries the depth such JDs ask for",
            "stretch_note": years_stretch_note(jd_text),
        }
    if SENIOR_JD.search(blob) and SWE_JD.search(blob):
        note = years_stretch_note(jd_text)
        return {
            "folder": "software-engineer",
            "reason": "Senior/lead/manager software title - prepare on tech overlap, do not refuse on years",
            "stretch_note": note,
        }
    if SWE_JD.search(blob):
        if re.search(r"\bjava\b", blob) or "spring" in blob:
            return {
                "folder": "java-developer",
                "reason": "Java/Spring on the JD",
                "stretch_note": years_stretch_note(jd_text),
            }
        return {
            "folder": "software-engineer",
            "reason": "Software/engineering JD",
            "stretch_note": years_stretch_note(jd_text),
        }
    return {
        "folder": None,
        "reason": "Unknown role. Ask the user which base-cvs folder to use. Do not guess.",
        "stretch_note": years_stretch_note(jd_text),
    }


def assert_allowed(folder: str, job_title: str, jd_text: str):
    blob = f"{job_title}\n{jd_text}".lower()
    if folder == "coding-teacher" and any(w in blob for w in ("engineer", "senior", "qa engineer", "system developer")):
        raise SystemExit("BLOCKED: coding-teacher master is not for engineering JDs.")
    if folder == "mental-health" and SWE_JD.search(blob):
        raise SystemExit("BLOCKED: mental-health master is not for engineering JDs.")


if __name__ == "__main__":
    import sys
    title = sys.argv[1] if len(sys.argv) > 1 else ""
    jd = " ".join(sys.argv[2:]) or title
    print(json.dumps(pick_base(title, jd), indent=2))
