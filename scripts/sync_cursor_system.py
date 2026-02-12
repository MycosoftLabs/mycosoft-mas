"""
Sync Mycosoft workspace Cursor assets into the Cursor system (user-level).

Scans ALL repos in the Mycosoft workspace for .cursor folders and merges:
  - rules/*.mdc
  - agents/*.md
  - skills/<name>/SKILL.md

Destination: user's Cursor directory (~/.cursor/ or %USERPROFILE%\\.cursor)

This ensures rules, agents, and skills are available in Cursor globally,
not only when a specific workspace is open. When agents, rules, or skills
are created or updated in any repo, running this script registers them
in the Cursor system so all agents can talk to all sub-agents, use all
rules, and have context across the entire platform.

Usage:
  python scripts/sync_cursor_system.py          # Sync all repos
  python scripts/sync_cursor_system.py --watch  # Watch for changes (daemon)

Optional env:
  CURSOR_USER_DIR  — User .cursor directory (default: %USERPROFILE%\\.cursor)
  CODE_ROOT        — Mycosoft CODE root (default: auto-detect from script path)
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent  # MAS repo
CODE_ROOT = Path(os.environ.get("CODE_ROOT", REPO_ROOT.parent.parent))  # C:\...\CODE

USER_HOME = Path(os.environ.get("USERPROFILE", os.environ.get("HOME", "")))
if not USER_HOME or not USER_HOME.is_dir():
    USER_HOME = Path.home()
CURSOR_USER = Path(os.environ.get("CURSOR_USER_DIR", USER_HOME / ".cursor"))

# All known repos in the Mycosoft workspace (ordered by priority, MAS first)
REPOS = [
    CODE_ROOT / "MAS" / "mycosoft-mas",
    CODE_ROOT / "WEBSITE" / "website",
    CODE_ROOT / "MINDEX" / "mindex",
    CODE_ROOT / "mycobrain",
    CODE_ROOT / "NATUREOS" / "NatureOS",
    CODE_ROOT / "Mycorrhizae",
    CODE_ROOT / "MAS" / "NLM",
    CODE_ROOT / "MAS" / "sdk",
    CODE_ROOT / "platform-infra",
]

# ── Sync Functions ────────────────────────────────────────────────────────────

def sync_rules_from(cursor_ws: Path, dst: Path) -> int:
    src = cursor_ws / "rules"
    if not src.is_dir():
        return 0
    dst.mkdir(parents=True, exist_ok=True)
    count = 0
    for f in src.glob("*.mdc"):
        t = dst / f.name
        # Overwrite if source is newer or doesn't exist
        if not t.exists() or f.stat().st_mtime > t.stat().st_mtime:
            shutil.copy2(f, t)
            count += 1
    return count


def sync_agents_from(cursor_ws: Path, dst: Path) -> int:
    src = cursor_ws / "agents"
    if not src.is_dir():
        return 0
    dst.mkdir(parents=True, exist_ok=True)
    count = 0
    for f in src.glob("*.md"):
        t = dst / f.name
        if not t.exists() or f.stat().st_mtime > t.stat().st_mtime:
            shutil.copy2(f, t)
            count += 1
    return count


def sync_skills_from(cursor_ws: Path, dst: Path) -> int:
    src = cursor_ws / "skills"
    if not src.is_dir():
        return 0
    dst.mkdir(parents=True, exist_ok=True)
    count = 0
    for d in src.iterdir():
        if d.is_dir() and (d / "SKILL.md").exists():
            t = dst / d.name
            # Check if any file in source is newer
            needs_update = not t.exists()
            if t.exists():
                src_mtime = max(f.stat().st_mtime for f in d.rglob("*") if f.is_file())
                dst_mtime = max((f.stat().st_mtime for f in t.rglob("*") if f.is_file()), default=0)
                needs_update = src_mtime > dst_mtime
            if needs_update:
                if t.exists():
                    shutil.rmtree(t, ignore_errors=True)
                shutil.copytree(d, t)
                count += 1
    return count


def sync_all() -> dict:
    """Sync from all repos to user Cursor directory. Returns counts."""
    CURSOR_USER.mkdir(parents=True, exist_ok=True)
    rules_dst = CURSOR_USER / "rules"
    agents_dst = CURSOR_USER / "agents"
    skills_dst = CURSOR_USER / "skills"

    total = {"rules": 0, "agents": 0, "skills": 0, "repos": 0}

    for repo in REPOS:
        cursor_ws = repo / ".cursor"
        if not cursor_ws.is_dir():
            continue
        r = sync_rules_from(cursor_ws, rules_dst)
        a = sync_agents_from(cursor_ws, agents_dst)
        s = sync_skills_from(cursor_ws, skills_dst)
        if r or a or s:
            total["repos"] += 1
        total["rules"] += r
        total["agents"] += a
        total["skills"] += s

    return total


def watch_loop(interval: int = 30):
    """Watch for changes and sync periodically."""
    print(f"[sync_cursor_system] Watching for changes every {interval}s...", file=sys.stderr)
    while True:
        try:
            counts = sync_all()
            if counts["rules"] or counts["agents"] or counts["skills"]:
                print(
                    f"[sync_cursor_system] Synced: rules={counts['rules']}, "
                    f"agents={counts['agents']}, skills={counts['skills']} "
                    f"from {counts['repos']} repos",
                    file=sys.stderr,
                )
        except Exception as e:
            print(f"[sync_cursor_system] Error: {e}", file=sys.stderr)
        time.sleep(interval)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Cursor assets from workspace to user Cursor system")
    parser.add_argument("--watch", action="store_true", help="Watch for changes and sync periodically")
    parser.add_argument("--interval", type=int, default=30, help="Watch interval in seconds (default: 30)")
    args = parser.parse_args()

    if args.watch:
        watch_loop(args.interval)
        return 0  # Never reached

    counts = sync_all()
    print(
        f"Synced to Cursor system ({CURSOR_USER}): "
        f"rules={counts['rules']}, agents={counts['agents']}, skills={counts['skills']} "
        f"from {counts['repos']} repos",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
