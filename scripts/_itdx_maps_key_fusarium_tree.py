"""Scan Fusarium trees for AIza / FUSARIUM_*GOOGLE* assignments. Fingerprints only."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

ROOTS = [
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\FUSARIUM"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website-itdx-codex-v13"),
]
SKIP = {".git", "node_modules", ".next", "dist", "__pycache__", ".venv"}


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> None:
    hashes: dict[str, int] = {}
    newest: list[tuple[float, str]] = []
    for root in ROOTS:
        if not root.exists():
            print("ABSENT", root)
            continue
        print("ROOT", root)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP]
            for name in filenames:
                path = Path(dirpath) / name
                try:
                    st = path.stat()
                except OSError:
                    continue
                if st.st_size > 300_000:
                    continue
                lower = name.lower()
                if not (
                    lower.endswith((".env", ".local", ".md", ".json", ".yml", ".yaml", ".txt", ".ps1", ".sh"))
                    or "env" in lower
                    or "credential" in lower
                    or "google" in lower
                    or "maps" in lower
                ):
                    continue
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if "AIza" not in text and "FUSARIUM_" not in text:
                    continue
                printed = False
                for line in text.splitlines():
                    if "AIza" not in line and not (
                        "FUSARIUM_" in line and "GOOGLE" in line.upper() and "=" in line
                    ):
                        continue
                    if "=" not in line:
                        continue
                    var, value = line.split("=", 1)
                    var = var.strip().lstrip("#").strip()
                    value = value.strip().strip('"').strip("'")
                    if value.startswith("AIza") and len(value) >= 20:
                        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
                        hashes[digest] = hashes.get(digest, 0) + 1
                        if not printed:
                            print("FILE", iso_mtime(path), path)
                            printed = True
                        print(f"  {var} len={len(value)} sha256_12={digest}")
                        newest.append((st.st_mtime, f"{digest} {var} {path}"))
                    elif "FUSARIUM" in var.upper() and "GOOGLE" in var.upper():
                        if not printed:
                            print("FILE", iso_mtime(path), path)
                            printed = True
                        print(f"  {var} non-AIza len={len(value)}")
    print("DISTINCT", hashes)
    if newest:
        newest.sort(reverse=True)
        print("NEWEST_AIZA")
        for _, row in newest[:15]:
            print(" ", row)


if __name__ == "__main__":
    main()
