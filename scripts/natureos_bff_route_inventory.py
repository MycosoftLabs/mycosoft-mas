#!/usr/bin/env python3
"""
Count Next.js App Router API routes under WEBSITE/website/app/api/natureos (NatureOS BFF).

Default discovery: CODE_ROOT/WEBSITE/website/app/api/natureos where CODE_ROOT is
grandparent of this MAS repo (…/CODE).

Usage:
  python scripts/natureos_bff_route_inventory.py
  python scripts/natureos_bff_route_inventory.py /path/to/website/app/api/natureos
"""
from __future__ import annotations

import sys
from pathlib import Path

MAS_ROOT = Path(__file__).resolve().parent.parent
CODE_ROOT = MAS_ROOT.parent.parent
DEFAULT_BFF = CODE_ROOT / "WEBSITE" / "website" / "app" / "api" / "natureos"


def main() -> None:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_BFF
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        sys.exit(2)
    routes = sorted({p.parent for p in root.rglob("route.ts")})
    print(f"natureos_bff_root={root}")
    print(f"route_handlers={len(routes)}")
    for p in routes:
        rel = p.relative_to(root)
        print(f"  {rel.as_posix()}")


if __name__ == "__main__":
    main()
