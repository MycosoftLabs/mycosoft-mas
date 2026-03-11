"""
MICA / MINDEX Merkle root builder.

- canonical encoding = deterministic CBOR
- hash = BLAKE3-256
- Merkle nodes duplicate the last hash on odd levels
- event roots: temporal + spatial buckets
- self/world roots: fixed slot order
- thought roots: self + world + event (+ optional truth/policy/prior)

See merkle/mica_merkle_spec/README.md for full architecture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

import cbor2
from blake3 import blake3


DOMAIN_EVENT_LEAF = b"mica:leaf:event:v1"
DOMAIN_WORLD_SLOT = b"mica:leaf:world_slot:v1"
DOMAIN_SNAPSHOT_OBJECT = b"mica:object:snapshot:v1"
DOMAIN_MERKLE_NODE = b"mica:node:v1"
DOMAIN_ROOT_RECORD = b"mica:object:root_record:v1"
DOMAIN_THOUGHT_CONTEXT = b"mica:object:thought_context:v1"
DOMAIN_EVENT_ROOT = b"mica:root:event:v1"
DOMAIN_AMENDMENT_ROOT = b"mica:root:amendment:v1"

SELF_SLOT_ORDER = [
    "identity",
    "persona",
    "policy",
    "safety",
    "agent_graph",
    "active_tasks",
    "tool_registry",
    "memory_heads",
    "filesystem_heads",
    "service_health",
    "network_status",
    "open_sessions",
]

WORLD_SLOT_ORDER = [
    "device_registry",
    "device_health",
    "crep_summary",
    "nlm_summary",
    "earth_sim_summary",
    "environment_feeds",
    "forecast_state",
    "anomaly_state",
    "map_state",
    "external_alerts",
]


def canonical_cbor(obj: object) -> bytes:
    """Encode using RFC 8949 deterministic/canonical ordering."""
    return cbor2.dumps(obj, canonical=True)


def hash_with_domain(domain: bytes, body: bytes) -> bytes:
    return blake3(domain + body).digest(length=32)


def hex32(digest: bytes) -> str:
    return digest.hex()


def leaf_hash_from_cbor_object(obj: object) -> bytes:
    return hash_with_domain(DOMAIN_EVENT_LEAF, canonical_cbor(obj))


def world_slot_hash(slot_name: str, data: object) -> bytes:
    """Hash a world slot payload for Merkle world root. Domain-separated by slot name."""
    payload = {1: slot_name, 2: data}
    return hash_with_domain(DOMAIN_WORLD_SLOT, canonical_cbor(payload))


def merkle_node_hash(left: bytes, right: bytes) -> bytes:
    return blake3(DOMAIN_MERKLE_NODE + left + right).digest(length=32)


def merkle_root(ordered_hashes: Sequence[bytes]) -> bytes:
    """Build a binary Merkle root. Empty invalid; single element = that element."""
    if not ordered_hashes:
        raise ValueError("cannot build merkle root for empty member list")

    level = list(ordered_hashes)
    if len(level) == 1:
        return level[0]

    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        next_level: list[bytes] = []
        for i in range(0, len(level), 2):
            next_level.append(merkle_node_hash(level[i], level[i + 1]))
        level = next_level
    return level[0]


def thought_hash_from_cbor_object(obj: object) -> bytes:
    return hash_with_domain(DOMAIN_THOUGHT_CONTEXT, canonical_cbor(obj))


@dataclass(frozen=True)
class EventIndexRow:
    event_hash: bytes
    event_time_ns: int
    device_id: str
    event_id: str
    h3_cell: Optional[str] = None


@dataclass(frozen=True)
class RootRecord:
    root_type: str
    root_hash: bytes
    tick_id: Optional[int]
    tick_start_ns: Optional[int]
    tick_width_ns: Optional[int]
    bucket_id: Optional[str]
    status: str
    child_count: int
    manifest_hash: bytes
    previous_root_hash: Optional[bytes] = None
    amendment_of_hash: Optional[bytes] = None
    labels: dict[str, str] = field(default_factory=dict)


def manifest_hash(member_hashes: Sequence[bytes]) -> bytes:
    manifest_obj = {1: 1, 2: list(member_hashes), 3: len(member_hashes)}
    return hash_with_domain(b"mica:object:manifest:v1", canonical_cbor(manifest_obj))


def event_sort_key(e: EventIndexRow) -> tuple[int, str, str, bytes]:
    return (e.event_time_ns, e.device_id, e.event_id, e.event_hash)


class EventRootBuilder:
    def __init__(self, tick_width_ns: int) -> None:
        if tick_width_ns <= 0:
            raise ValueError("tick_width_ns must be > 0")
        self.tick_width_ns = tick_width_ns

    def build_temporal_root(
        self,
        tick_id: int,
        events: Sequence[EventIndexRow],
        status: str = "provisional",
        previous_root_hash: bytes | None = None,
    ) -> RootRecord:
        if not events:
            raise ValueError("temporal root requires at least one event")
        ordered = sorted(events, key=event_sort_key)
        member_hashes = [e.event_hash for e in ordered]
        root_hash = merkle_root(member_hashes)
        return RootRecord(
            root_type="temporal",
            root_hash=root_hash,
            tick_id=tick_id,
            tick_start_ns=tick_id * self.tick_width_ns,
            tick_width_ns=self.tick_width_ns,
            bucket_id=None,
            status=status,
            child_count=len(member_hashes),
            manifest_hash=manifest_hash(member_hashes),
            previous_root_hash=previous_root_hash,
        )

    def build_spatial_bucket_roots(
        self,
        tick_id: int,
        events: Sequence[EventIndexRow],
        status: str = "provisional",
    ) -> list[RootRecord]:
        by_cell: dict[str, list[EventIndexRow]] = {}
        for e in events:
            if e.h3_cell is None:
                continue
            by_cell.setdefault(e.h3_cell, []).append(e)

        results: list[RootRecord] = []
        for cell, members in sorted(by_cell.items(), key=lambda kv: kv[0]):
            ordered = sorted(members, key=event_sort_key)
            member_hashes = [e.event_hash for e in ordered]
            root_hash = merkle_root(member_hashes)
            results.append(
                RootRecord(
                    root_type="spatial_bucket",
                    root_hash=root_hash,
                    tick_id=tick_id,
                    tick_start_ns=tick_id * self.tick_width_ns,
                    tick_width_ns=self.tick_width_ns,
                    bucket_id=cell,
                    status=status,
                    child_count=len(member_hashes),
                    manifest_hash=manifest_hash(member_hashes),
                )
            )
        return results

    def build_spatial_root(
        self,
        tick_id: int,
        bucket_roots: Sequence[RootRecord],
        status: str = "provisional",
        previous_root_hash: bytes | None = None,
    ) -> RootRecord:
        if not bucket_roots:
            raise ValueError("spatial root requires at least one spatial bucket root")
        ordered = sorted(bucket_roots, key=lambda r: (r.bucket_id or "", r.root_hash))
        member_hashes = [r.root_hash for r in ordered]
        root_hash = merkle_root(member_hashes)
        return RootRecord(
            root_type="spatial",
            root_hash=root_hash,
            tick_id=tick_id,
            tick_start_ns=tick_id * self.tick_width_ns,
            tick_width_ns=self.tick_width_ns,
            bucket_id=None,
            status=status,
            child_count=len(member_hashes),
            manifest_hash=manifest_hash(member_hashes),
            previous_root_hash=previous_root_hash,
        )

    def build_event_root(
        self,
        tick_id: int,
        temporal_root: RootRecord,
        spatial_root: Optional[RootRecord],
        status: str = "provisional",
        previous_root_hash: bytes | None = None,
    ) -> RootRecord:
        payload = {
            1: 1,
            2: tick_id,
            3: temporal_root.root_hash,
            4: spatial_root.root_hash if spatial_root else None,
        }
        root_hash = hash_with_domain(DOMAIN_EVENT_ROOT, canonical_cbor(payload))
        member_hashes = [temporal_root.root_hash]
        if spatial_root:
            member_hashes.append(spatial_root.root_hash)
        return RootRecord(
            root_type="event",
            root_hash=root_hash,
            tick_id=tick_id,
            tick_start_ns=tick_id * self.tick_width_ns,
            tick_width_ns=self.tick_width_ns,
            bucket_id=None,
            status=status,
            child_count=len(member_hashes),
            manifest_hash=manifest_hash(member_hashes),
            previous_root_hash=previous_root_hash,
        )


class SnapshotRootBuilder:
    def build_slot_root(
        self,
        root_type: str,
        tick_id: int,
        tick_width_ns: int,
        slot_hashes: dict[str, bytes],
        status: str = "provisional",
        previous_root_hash: bytes | None = None,
    ) -> RootRecord:
        if root_type not in {"self", "world", "truth_mirror"}:
            raise ValueError(f"unsupported root_type: {root_type}")
        if root_type == "self":
            order = SELF_SLOT_ORDER
        elif root_type == "world":
            order = WORLD_SLOT_ORDER
        else:
            order = sorted(slot_hashes.keys())

        member_hashes: list[bytes] = []
        for slot in order:
            digest = slot_hashes.get(slot)
            if digest is not None:
                member_hashes.append(digest)

        if not member_hashes:
            raise ValueError(f"{root_type} root requires at least one member")

        root_hash = merkle_root(member_hashes)
        return RootRecord(
            root_type=root_type,
            root_hash=root_hash,
            tick_id=tick_id,
            tick_start_ns=tick_id * tick_width_ns,
            tick_width_ns=tick_width_ns,
            bucket_id=None,
            status=status,
            child_count=len(member_hashes),
            manifest_hash=manifest_hash(member_hashes),
            previous_root_hash=previous_root_hash,
        )


class ThoughtRootBuilder:
    def build_thought_root(
        self,
        tick_id: int,
        thought_time_ns: int,
        actor_id: str,
        self_root_hash: bytes,
        world_root_hash: bytes,
        event_root_hash: bytes,
        truth_mirror_root_hash: bytes | None = None,
        previous_thought_root_hash: bytes | None = None,
        policy_root_hash: bytes | None = None,
        session_id: str | None = None,
        evidence_root_hashes: Optional[Sequence[bytes]] = None,
        labels: Optional[dict[str, str]] = None,
    ) -> tuple[bytes, dict]:
        thought_obj: dict = {
            1: 1,
            2: tick_id,
            3: thought_time_ns,
            4: actor_id,
            6: self_root_hash,
            7: world_root_hash,
            8: event_root_hash,
        }
        if session_id is not None:
            thought_obj[5] = session_id
        if truth_mirror_root_hash is not None:
            thought_obj[9] = truth_mirror_root_hash
        if previous_thought_root_hash is not None:
            thought_obj[10] = previous_thought_root_hash
        if policy_root_hash is not None:
            thought_obj[11] = policy_root_hash
        if evidence_root_hashes:
            thought_obj[12] = list(evidence_root_hashes)
        if labels:
            thought_obj[13] = labels
        return thought_hash_from_cbor_object(thought_obj), thought_obj


def build_inclusion_proof(ordered_hashes: Sequence[bytes], target_hash: bytes) -> list[tuple[str, bytes]]:
    """Build Merkle proof for target leaf. Returns list of ('left'|'right', sibling_hash)."""
    if not ordered_hashes:
        raise ValueError("cannot prove inclusion in empty list")
    try:
        index = list(ordered_hashes).index(target_hash)
    except ValueError as exc:
        raise ValueError("target hash not present in ordered hash list") from exc

    level = list(ordered_hashes)
    proof: list[tuple[str, bytes]] = []

    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        is_right_node = index % 2 == 1
        sibling_index = index - 1 if is_right_node else index + 1
        sibling_hash = level[sibling_index]
        proof.append(("left" if is_right_node else "right", sibling_hash))
        next_level: list[bytes] = []
        for i in range(0, len(level), 2):
            next_level.append(merkle_node_hash(level[i], level[i + 1]))
        index //= 2
        level = next_level
    return proof
