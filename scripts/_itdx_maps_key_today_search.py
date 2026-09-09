"""Search recent/Fusarium env files for Google keys. Fingerprints only."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

ROOTS = [
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT"),
    Path(r"C:\Users\Owner1\.cursor"),
    Path(r"C:\Users\Owner1\Documents"),
    Path(r"C:\Users\admin2\.cursor"),
]
FILE_NAMES = {
    ".env.local",
    ".credentials.local",
    ".credentials.maps.env",
    ".env",
}
NAME_HINTS = ("GOOGLE", "FUSARIUM", "GEMINI", "MAPS", "MAP_TILES", "GMAPS")


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def walk() -> None:
    seen: set[str] = set()
    hashes: dict[str, list[str]] = {}
    scanned = 0
    for root in ROOTS:
        if not root.exists():
            print("ROOT_ABSENT", root)
            continue
        print("ROOT", root)
        for dirpath, dirnames, filenames in os_walk(root):
            dirnames[:] = [
                d
                for d in dirnames
                if d not in {".git", "node_modules", ".next", "dist", "__pycache__", ".venv", "venv"}
            ]
            for name in filenames:
                lower = name.lower()
                if name not in FILE_NAMES and not (
                    "fusarium" in lower and (lower.endswith(".env") or lower.endswith(".local") or "credential" in lower)
                ):
                    if not (
                        ("google" in lower or "maps" in lower or "fusarium" in lower)
                        and (lower.endswith(".env") or lower.endswith(".env.local") or "credential" in lower)
                    ):
                        continue
                path = Path(dirpath) / name
                key = str(path)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    if path.stat().st_size > 1_500_000:
                        continue
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
                    if not value or not any(h in var.upper() for h in NAME_HINTS):
                        continue
                    if not (value.startswith("AIza") or "FUSARIUM" in var.upper() or "MAPS" in var.upper()):
                        continue
                    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
                    if not printed:
                        print("FILE", iso_mtime(path), path)
                        printed = True
                    print(f"  {var} len={len(value)} prefix={value[:4]} sha256_12={digest}")
                    hashes.setdefault(digest, []).append(f"{var}@{path.name}")
    print("SCANNED", scanned, "DISTINCT", len(hashes))
    for digest, aliases in hashes.items():
        print("HASH", digest, "count", len(aliases))


def os_walk(root: Path):
    import os

    return os.walk(root)


if __name__ == "__main__":
    walk()
