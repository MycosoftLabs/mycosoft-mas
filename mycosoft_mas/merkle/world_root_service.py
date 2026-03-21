"""
Merkle world root service for MYCA consciousness grounding.

Builds provable world state roots from device registry, CREP, NLM, Earth2, etc.
Anchors responses in verifiable data via Merkle roots.
"""

from __future__ import annotations

import time
from typing import Any

from mycosoft_mas.merkle.root_builder import (
    WORLD_SLOT_ORDER,
    SnapshotRootBuilder,
    world_slot_hash,
)

TICK_WIDTH_NS = 1_000_000_000  # 1 second


def build_world_root(slot_data: dict[str, Any]) -> str:
    """
    Build Merkle world root from slot data.

    slot_data: map of slot name (from WORLD_SLOT_ORDER) to JSON-serializable data.
    Only slots present in slot_data are hashed; at least one required.

    Returns hex string of the world root hash.
    """
    slot_hashes: dict[str, bytes] = {}
    for slot, data in slot_data.items():
        if slot not in WORLD_SLOT_ORDER:
            continue
        slot_hashes[slot] = world_slot_hash(slot, data)
    if not slot_hashes:
        raise ValueError("world root requires at least one slot")
    tick_id = int(time.time_ns() // TICK_WIDTH_NS)
    srb = SnapshotRootBuilder()
    record = srb.build_slot_root(
        root_type="world",
        tick_id=tick_id,
        tick_width_ns=TICK_WIDTH_NS,
        slot_hashes=slot_hashes,
        status="provisional",
    )
    return record.root_hash.hex()
