# -*- coding: utf-8 -*-
"""Applicant config.

All scripts read the applicant's identity from profile/user.json (which is
gitignored — your real data never enters version control). Copy
profile/user.example.json to profile/user.json and edit it.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER_PATH = ROOT / "profile" / "user.json"
EXAMPLE_FALLBACK_ERROR = (
    "No profile/user.json. Copy profile/user.example.json → profile/user.json "
    "and fill in your own details. Never commit your real user.json."
)


def load() -> dict:
    if USER_PATH.exists():
        return json.loads(USER_PATH.read_text(encoding="utf-8"))
    return json.loads((ROOT / "profile" / "user.example.json").read_text(encoding="utf-8"))


def _req(cfg: dict, key: str):
    v = cfg.get(key)
    if not v or str(v).startswith("REPLACE"):
        raise SystemExit(f"profile/user.json is missing or still has the placeholder for '{key}'.")
    return v


def prefix(cfg: dict | None = None) -> str:
    """Underscored name used in output filenames, e.g. Jane_Mbugua → Jane_Mbugua_<Role>_Resume.pdf."""
    cfg = cfg or load()
    return _req(cfg, "filename_prefix").replace(" ", "_")


def resume_re(cfg: dict | None = None) -> re.Pattern:
    p = re.escape(prefix(cfg))
    return re.compile(rf"^{p}_.+_Resume\.pdf$", re.I)


def letter_re(cfg: dict | None = None) -> re.Pattern:
    p = re.escape(prefix(cfg))
    return re.compile(rf"^{p}_.+_Cover_Letter\.pdf$", re.I)


def combined_re(cfg: dict | None = None) -> re.Pattern:
    p = re.escape(prefix(cfg))
    return re.compile(rf"^{p}_.+_Combined\.pdf$", re.I)


def required_links(cfg: dict | None = None) -> set[str]:
    """Clickable URLs the software-track CV must carry (mailto + portfolio links)."""
    cfg = cfg or load()
    return {_req_like(u) for u in (cfg.get("required_links") or []) if u}


def link_map(cfg: dict | None = None) -> list[tuple[str, str]]:
    """(label, url) pairs injected into legacy DOCX headers, e.g. LinkedIn -> your profile."""
    cfg = cfg or load()
    return [(pair["label"], pair["url"]) for pair in (cfg.get("link_labels") or [])]


def preview_dir(cfg: dict | None = None) -> Path:
    cfg = cfg or load()
    d = Path(cfg.get("preview_dir") or "~/Documents/jobpack-preview").expanduser()
    return d


def _req_like(url: str) -> str:
    return url.rstrip("/")
