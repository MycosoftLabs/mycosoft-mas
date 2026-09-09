"""Fingerprint Google/Fusarium keys without printing values."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

NAME_NEEDLES = (
    "GOOGLE_MAPS",
    "GOOGLE_MAP",
    "GOOGLE_API_KEY",
    "FUSARIUM",
    "GEMINI",
    "GOOGLE_AI",
    "MAP_TILES",
    "MAPS_API",
)

FILES = [
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.credentials.local"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.credentials.maps.env"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.env"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas\.env.local"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.env.local"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.credentials.local"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website-itdx-codex-v13\.env.local"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website-itdx-codex-v13\.credentials.local"),
]


def iso_mtime(path: Path) -> str:
    ts = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def interesting(name: str) -> bool:
    upper = name.upper()
    return any(n in upper for n in NAME_NEEDLES)


def main() -> None:
    rows: list[tuple[str, str, str, int, str, str, str]] = []
    for path in FILES:
        print("FILE", path.exists(), iso_mtime(path) if path.exists() else "-", path)
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            name = name.strip()
            value = value.strip().strip('"').strip("'")
            if not interesting(name) or not value:
                continue
            digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
            prefix = value[:4] if len(value) >= 4 else "NONE"
            rows.append((iso_mtime(path), path.name, name, len(value), prefix, digest, str(path)))
    print("KEYS")
    by_hash: dict[str, list[str]] = {}
    for mtime, filename, name, length, prefix, digest, full in rows:
        print(f"  {mtime} {filename} {name} len={length} prefix={prefix} sha256_12={digest}")
        by_hash.setdefault(digest, []).append(f"{name}@{filename}")
    print("DISTINCT_VALUES", len(by_hash))
    for digest, aliases in by_hash.items():
        print("  HASH", digest, "aliases", ",".join(aliases))


if __name__ == "__main__":
    main()
