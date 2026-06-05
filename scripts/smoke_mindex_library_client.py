#!/usr/bin/env python3
"""Smoke test MindexLibraryClient against MINDEX VM (skips gracefully if LAN down)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


async def main() -> int:
    from mycosoft_mas.integrations.mindex_library_client import MindexLibraryClient

    client = MindexLibraryClient()
    health = await client.health_check()
    if not health.get("reachable"):
        print(f"SKIP: MINDEX unreachable — {health.get('error', 'unknown')}")
        return 0
    if health.get("status") == "auth_required":
        print(f"SKIP: MINDEX reachable but auth missing — {health.get('error')}")
        return 0

    print(f"OK: catalog db_registered_total={health.get('db_registered_total')}")
    blobs = await client.list_blobs(category="acoustic", limit=3)
    print(f"OK: list_blobs total={blobs.get('total')} items={len(blobs.get('items') or [])}")
    tags = await client.get_human_tags(limit=5)
    print(f"OK: human-tags total={tags.get('total')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
