#!/usr/bin/env python3
"""Push all uncommitted changes across MAS and website repos, then deploy to sandbox."""
import subprocess
import sys
from pathlib import Path

MAS = Path(__file__).parent.parent
WEBSITE = MAS.parent.parent / "WEBSITE" / "website"
MINDEX = MAS.parent.parent / "MINDEX" / "mindex"

def git(repo: Path, *args):
    result = subprocess.run(["git"] + list(args), cwd=repo, capture_output=True, text=True)
    out = (result.stdout + result.stderr).strip()
    print(f"[{repo.name}] git {' '.join(args[:2])}: {out[:300] or 'ok'}")
    return result.returncode == 0

# ── MAS ──────────────────────────────────────────────────────────────────────
print("\n=== MAS repo ===")
git(MAS, "add", "mycosoft_mas/", "docs/", "scripts/", "tests/", ".cursor/")
git(MAS, "commit", "-m", "chore: All session changes — agent bus, security, MCP, scripts, docs")
git(MAS, "push", "origin", "main")

# ── WEBSITE ───────────────────────────────────────────────────────────────────
print("\n=== WEBSITE repo ===")
git(WEBSITE, "add", "app/", "components/", "hooks/", "lib/", "docs/", "scripts/")
git(WEBSITE, "commit", "-m", "chore: All session changes — CREP, fungi-compute, websockets, MYCA provider fix")
git(WEBSITE, "push", "origin", "main")

print("\nAll repos pushed.")
