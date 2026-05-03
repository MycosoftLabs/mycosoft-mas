#!/usr/bin/env python3
"""
NatureOS BFF route inventory — May 2, 2026

Scans WEBSITE/website/app/api/natureos for route.ts files and prints
exported HTTP method handlers and the first upstream target hint
(fetch( URL, MINDEX_API, MAS_API, NATUREOS, core-api, etc.)).

Run from MAS repo root (or any cwd):
  python scripts/natureos_bff_route_inventory.py
  python scripts/natureos_bff_route_inventory.py C:/path/to/WEBSITE/website

Or from website repo with explicit root:
  python /path/to/mas/scripts/natureos_bff_route_inventory.py .
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def find_website_api_root() -> Path:
    if len(sys.argv) > 1:
        p = Path(sys.argv[1]).resolve()
        if p.name == "natureos" and p.is_dir():
            return p
        n = p / "app" / "api" / "natureos"
        if n.is_dir():
            return n
        return p
    # MAS repo layout: ../../WEBSITE/website (from CODE/MAS/mycosoft-mas)
    here = Path(__file__).resolve().parent.parent
    code_root = here.parent.parent
    for candidate in (
        code_root / "WEBSITE" / "website" / "app" / "api" / "natureos",
        here / "WEBSITE" / "website" / "app" / "api" / "natureos",
    ):
        resolved = candidate.resolve()
        if resolved.is_dir():
            return resolved
    return (here / "WEBSITE" / "website" / "app" / "api" / "natureos")


METHOD_RE = re.compile(r"export\s+async\s+function\s+(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\b")
FETCH_HINT = re.compile(
    r"fetch\s*\(\s*[`'\"]([^`'\"]+)[`'\"]"
    r"|getEnv\w*\s*\("
    r"|\$\{[^}]+MINDEX[^}]*\}"
    r"|\$\{[^}]+MAS_API[^}]*\}"
    r"|\$\{[^}]+NATUREOS[^}]*\}"
    r"|process\.env\.\w+"
)


def first_fetch_hints(text: str, limit: int = 3) -> list[str]:
    hits: list[str] = []
    for m in FETCH_HINT.finditer(text):
        g = m.group(0) if m.lastindex is None or m.lastindex < 1 else m.group(1) or m.group(0)
        g = (g or "").strip()
        if len(g) > 120:
            g = g[:117] + "..."
        if g and g not in hits:
            hits.append(g)
        if len(hits) >= limit:
            break
    return hits


def main() -> int:
    root = find_website_api_root()
    if not root.is_dir():
        print(f"NatureOS BFF path not found: {root}", file=sys.stderr)
        return 1

    route_files = sorted(root.rglob("route.ts")) + sorted(root.rglob("route.js"))
    print(f"# NatureOS BFF route inventory: {len(route_files)} route files under {root}\n")

    for f in route_files:
        rel = f.relative_to(root) if f.is_file() else f
        text = f.read_text(encoding="utf-8", errors="replace")
        methods = METHOD_RE.findall(text)
        methods_str = ", ".join(methods) if methods else "(no exported GET/POST — check re-exports)"
        hints = first_fetch_hints(text)
        hint_str = " | ".join(hints) if hints else "(no fetch string literal in file — may use shared helper)"
        print(f"{rel} :: {methods_str} :: {hint_str}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
