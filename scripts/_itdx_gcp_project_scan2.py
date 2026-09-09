"""Broader local hunt for GCP project IDs. Never print keys."""

from __future__ import annotations

import re
from pathlib import Path

AIZA = re.compile(r"AIza[0-9A-Za-z_-]{10,}")
PROJECTISH = re.compile(
    r"(?:GCP_PROJECT|GOOGLE_CLOUD_PROJECT|GEE_PROJECT_ID|FIREBASE_PROJECT|NEXT_PUBLIC_FIREBASE_PROJECT_ID|"
    r"GCLOUD_PROJECT|project_id|PROJECT_ID)\s*[:=]\s*['\"]?([a-z0-9][a-z0-9-]{4,61}[a-z0-9])",
    re.I,
)
CONSOLE = re.compile(r"console\.cloud\.google\.com/[^\s)\"']+")
ROOTS = [
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\docs"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\docs"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\docs"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website"),
]


def main() -> None:
    found: dict[str, list[str]] = {}
    scanned = 0
    for root in ROOTS:
        if not root.exists():
            continue
        if root.is_file():
            candidates = [root]
        else:
            candidates = []
            for pat in ("*.md", "*.env*", ".credentials.local", "*.json", "*.yml", "*.yaml"):
                candidates.extend(root.glob(pat))
                if root.name in {"docs", "CODE"}:
                    candidates.extend(root.rglob(pat))
        for path in candidates:
            if not path.is_file() or path.stat().st_size > 1_500_000:
                continue
            if any(part in {".git", "node_modules", ".next"} for part in path.parts):
                continue
            scanned += 1
            try:
                text = AIZA.sub("AIza***", path.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
            for match in PROJECTISH.finditer(text):
                found.setdefault(match.group(1), []).append(str(path))
            for match in CONSOLE.finditer(text):
                found.setdefault(match.group(0), []).append(str(path))
    print("SCANNED", scanned)
    for value, paths in sorted(found.items()):
        print("HIT", value)
        for item in paths[:4]:
            print(" ", item)


if __name__ == "__main__":
    main()
