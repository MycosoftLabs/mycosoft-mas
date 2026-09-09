"""Last-look: Fusarium app envs + transcript mentions. Never print key values."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

ROOTS = [
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\FUSARIUM"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website-itdx-codex-v13"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website"),
]
TRANSCRIPTS = Path(r"C:\Users\Owner1\.cursor\projects\d-Users-admin2-Desktop-MYCOSOFT-CODE-MAS-mycosoft-mas\agent-transcripts")
DOCS = Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\docs")


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> None:
    print("ENV_FILES")
    for root in ROOTS:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules", ".next"}]
            for name in filenames:
                if not (name.startswith(".env") or name.endswith(".env") or name.startswith(".credentials")):
                    continue
                path = Path(dirpath) / name
                print(" ", iso_mtime(path), path)
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                for line in text.splitlines():
                    if "=" not in line or line.lstrip().startswith("#"):
                        continue
                    var, value = line.split("=", 1)
                    var = var.strip()
                    value = value.strip().strip('"').strip("'")
                    if value.startswith("AIza"):
                        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
                        print(f"    {var} sha256_12={digest} len={len(value)}")
                    elif "FUSARIUM" in var.upper() and "GOOGLE" in var.upper():
                        print(f"    {var} set len={len(value)}")
    print("DOC_HITS")
    if DOCS.exists():
        for path in sorted(DOCS.glob("*SEP09*"), key=lambda p: p.stat().st_mtime, reverse=True):
            text = path.read_text(encoding="utf-8", errors="replace")
            if "GOOGLE_MAPS" in text or "Fusarium" in text and "key" in text.lower():
                print(" ", iso_mtime(path), path.name)
    print("TRANSCRIPT_NAMES")
    if TRANSCRIPTS.exists():
        count = 0
        for path in TRANSCRIPTS.glob("*.jsonl"):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "FUSARIUM_" in text and "GOOGLE" in text:
                print(" ", path.name, "has FUSARIUM+GOOGLE")
                count += 1
            if "newest Fusarium" in text or "Fusarium Google key" in text:
                print(" ", path.name, "mentions newest Fusarium key")
        print(" scanned", count)


if __name__ == "__main__":
    main()
