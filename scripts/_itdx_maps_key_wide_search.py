"""Wider search for Fusarium/Google keys. Fingerprints only; never print values."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

ROOTS = [
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website-itdx-codex-v13"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"),
    Path(r"C:\Users\Owner1\.cursor\worktrees"),
    Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE"),
]
NAME_HINTS = (
    "GOOGLE",
    "FUSARIUM",
    "GEMINI",
    "MAPS",
    "MAP_TILES",
    "GMAPS",
)
FILE_GLOBS = (
    ".env",
    ".env.local",
    ".env.*",
    ".credentials.local",
    ".credentials.*",
    "*credentials*.env",
    "*maps*.env",
    "*fusarium*.env*",
    "*google*.env*",
)


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def interesting_name(name: str) -> bool:
    upper = name.upper()
    return any(h in upper for h in NAME_HINTS)


def main() -> None:
    files: list[Path] = []
    for root in ROOTS:
        if not root.exists():
            print("ROOT_ABSENT", root)
            continue
        print("ROOT", root)
        for glob in FILE_GLOBS:
            try:
                files.extend(p for p in root.glob(glob) if p.is_file())
            except OSError:
                continue
            # one-level children for worktrees
            try:
                for child in root.iterdir():
                    if child.is_dir() and not child.name.startswith(".git"):
                        files.extend(p for p in child.glob(glob) if p.is_file())
            except OSError:
                continue
    # also explicit deep-ish env in website worktrees
    extra_roots = [
        Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website-itdx-codex-v13"),
        Path(r"C:\Users\Owner1\.cursor\worktrees"),
    ]
    for root in extra_roots:
        if not root.exists():
            continue
        try:
            for p in root.rglob(".env.local"):
                if p.is_file() and p.stat().st_size < 2_000_000:
                    files.append(p)
            for p in root.rglob(".credentials.local"):
                if p.is_file() and p.stat().st_size < 2_000_000:
                    files.append(p)
        except OSError:
            continue

    seen_paths: set[str] = set()
    by_hash: dict[str, list[str]] = {}
    newest: list[tuple[str, str, str, int, str]] = []
    for path in files:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen_paths:
            continue
        seen_paths.add(key)
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        if any(part in {".git", "node_modules", ".next"} for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        printed_file = False
        for line in text.splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            name = name.strip()
            value = value.strip().strip('"').strip("'")
            if not interesting_name(name) or not value:
                continue
            if not (value.startswith("AIza") or "FUSARIUM" in name.upper() or "MAPS" in name.upper()):
                continue
            if not printed_file:
                print("FILE", iso_mtime(path), path)
                printed_file = True
            digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
            prefix = value[:4] if len(value) >= 4 else "NONE"
            print(f"  {name} len={len(value)} prefix={prefix} sha256_12={digest}")
            by_hash.setdefault(digest, []).append(f"{name}@{path.name}")
            newest.append((iso_mtime(path), name, digest, len(value), str(path)))
    print("DISTINCT", len(by_hash))
    for digest, aliases in by_hash.items():
        print("HASH", digest, "count", len(aliases), "sample", ",".join(aliases[:8]))
    print("SCANNED_FILES", len(seen_paths))


if __name__ == "__main__":
    main()
