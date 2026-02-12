#!/usr/bin/env python3
"""
Build .cursor/docs_manifest.json: list of all .md docs (path, title, date, repo).
Cursor agents use this for full doc discovery; run after adding many new docs.
Usage: python scripts/build_docs_manifest.py
"""
import json
import re
from pathlib import Path

# Repo roots relative to MAS repo root (script lives in MAS/scripts)
MAS_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOTS = [
    ("MAS", MAS_ROOT),
    ("WEBSITE", MAS_ROOT.parent / "WEBSITE" / "website"),
    ("MINDEX", MAS_ROOT.parent / "MINDEX" / "mindex"),
    ("MycoBrain", MAS_ROOT.parent / "mycobrain"),
    ("NatureOS", MAS_ROOT.parent / "NATUREOS" / "NatureOS"),
    ("Mycorrhizae", MAS_ROOT.parent / "Mycorrhizae" / "mycorrhizae-protocol"),
    ("NLM", MAS_ROOT.parent / "MAS" / "NLM"),
    ("platform-infra", MAS_ROOT.parent / "platform-infra"),
]

# Date in filename: _MMMDD_YYYY or _YYYY-MM-DD
DATE_PAT = re.compile(r"_?(?:([A-Z]{3})(\d{1,2})_(\d{4})|(\d{4})-(\d{2})-(\d{2}))")


def extract_date(name: str) -> str | None:
    m = DATE_PAT.search(name)
    if not m:
        return None
    if m.group(4):
        return f"{m.group(4)}-{m.group(5)}-{m.group(6)}"
    mon, day, year = m.group(1), m.group(2).zfill(2), m.group(3)
    return f"{year}-{mon}-{day}"  # approximate


def first_header(content: str) -> str:
    for line in content.splitlines():
        s = line.strip()
        if s.startswith("#"):
            return s.lstrip("#").strip()[:120]
    return ""


def scan_docs() -> list[dict]:
    out = []
    for repo, root in WORKSPACE_ROOTS:
        if not root.exists():
            continue
        docs_dir = root / "docs"
        if not docs_dir.exists():
            # Still scan repo for any .md
            for p in root.rglob("*.md"):
                if "node_modules" in p.parts or ".git" in p.parts:
                    continue
                try:
                    text = p.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    text = ""
                out.append({
                    "path": str(p.relative_to(root)),
                    "repo": repo,
                    "title": first_header(text) or p.stem,
                    "date": extract_date(p.name),
                })
            continue
        for p in docs_dir.rglob("*.md"):
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                text = ""
            rel = p.relative_to(root)
            out.append({
                "path": str(rel),
                "repo": repo,
                "title": first_header(text) or p.stem,
                "date": extract_date(p.name),
            })
    return out


def main():
    manifest = scan_docs()
    out_path = MAS_ROOT / ".cursor" / "docs_manifest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"count": len(manifest), "docs": manifest}, indent=2))
    print(f"Wrote {len(manifest)} docs to {out_path}")


if __name__ == "__main__":
    main()
