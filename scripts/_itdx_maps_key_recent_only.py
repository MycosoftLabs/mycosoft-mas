"""Fingerprint AIza keys in recent env/credential files only. No values printed."""

from __future__ import annotations

import hashlib
import os
import time
from datetime import datetime, timezone
from pathlib import Path

ROOTS = [
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE"),
    Path(r"C:\Users\Owner1\.cursor\plans"),
    Path(r"C:\Users\Owner1\Downloads"),
    Path(r"D:\Users\admin2\Downloads"),
]
CUTOFF = time.time() - 14 * 24 * 3600
SKIP = {".git", "node_modules", ".next", "dist", "__pycache__", ".venv"}


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def want_file(name: str) -> bool:
    lower = name.lower()
    return (
        name in {".env.local", ".credentials.local", ".credentials.maps.env", ".env"}
        or lower.endswith(".env")
        or lower.endswith(".env.local")
        or "credential" in lower
        or (lower.endswith(".json") and ("google" in lower or "maps" in lower or "fusarium" in lower))
    )


def main() -> None:
    hashes: dict[str, list[str]] = {}
    scanned = 0
    for root in ROOTS:
        if not root.exists():
            print("ABSENT", root)
            continue
        print("ROOT", root)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP]
            # skip huge website clones
            if any(part.startswith(".") and part.endswith("-sync") for part in Path(dirpath).parts):
                continue
            if any(part in {".main-sync", ".tmp-launch-inspect", "hotfix-bg-env"} for part in Path(dirpath).parts):
                continue
            for name in filenames:
                if not want_file(name):
                    continue
                path = Path(dirpath) / name
                try:
                    st = path.stat()
                except OSError:
                    continue
                if st.st_mtime < CUTOFF or st.st_size > 400_000:
                    continue
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                scanned += 1
                printed = False
                for line in text.splitlines():
                    if not line or line.lstrip().startswith("#") or "=" not in line:
                        continue
                    var, value = line.split("=", 1)
                    var = var.strip()
                    value = value.strip().strip('"').strip("'")
                    if not value.startswith("AIza"):
                        if "FUSARIUM" in var.upper() and "GOOGLE" in var.upper():
                            if not printed:
                                print("FILE", iso_mtime(path), path)
                                printed = True
                            print(f"  {var} non-AIza len={len(value)}")
                        continue
                    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
                    if not printed:
                        print("FILE", iso_mtime(path), path)
                        printed = True
                    print(f"  {var} len={len(value)} sha256_12={digest}")
                    hashes.setdefault(digest, []).append(f"{var}@{path}")
    print("SCANNED", scanned, "DISTINCT_AIZA", len(hashes))
    for digest, aliases in hashes.items():
        print("HASH", digest, "count", len(aliases), "first", aliases[0])


if __name__ == "__main__":
    main()
