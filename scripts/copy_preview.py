# -*- coding: utf-8 -*-
"""Copy an application pack into <preview_dir> (profile/user.json) for preview."""

from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from userconfig import prefix, preview_dir  # noqa: E402


def copy_pack(app_folder: Path):
    app_folder = Path(app_folder)
    dest = preview_dir() / app_folder.name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    pre = prefix()
    copied = []
    for p in app_folder.iterdir():
        # Sendables + workflow: PDFs named <Prefix>_*, APPLY, GATES, REVIEWER
        if p.name in {"APPLY.txt", "GATES.md", "REVIEWER.md", "VERIFY.txt", "preview.png"}:
            shutil.copy2(p, dest / p.name)
            copied.append(p.name)
            continue
        if p.suffix.lower() == ".pdf" and p.name.startswith(pre):
            shutil.copy2(p, dest / p.name)
            copied.append(p.name)
    return dest, copied


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: copy_preview.py <applications/pack_folder>")
    dest, copied = copy_pack(Path(sys.argv[1]))
    print(f"Copied {len(copied)} files to {dest}")
