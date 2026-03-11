"""
MICA / MINDEX Merkle root builder skeleton.

This file is deliberately opinionated and narrow:
- canonical encoding = deterministic CBOR
- hash = BLAKE3-256
- Merkle nodes duplicate the last hash on odd levels
- event roots are built from deterministic temporal + spatial buckets
- self/world roots are built from fixed slot order
- thought roots bind self + world + event (+ optional truth/policy/prior)

This is a service skeleton, not a full production daemon.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence

import cbor2
from blake3 import blake3


DOMAIN_EVENT_LEAF = b"mica:leaf:event:v1"
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


def snapshot_hash_from_cbor_object(obj: object) -> bytes:
    return hash_with_domain(DOMAIN_SNAPSHOT_OBJECT, canonical_cbor(obj))


def root_record_hash_from_cbor_object(obj: object) -> bytes:
    return hash_with_domain(DOMAIN_ROOT_RECORD, canonical_cbor(obj))


def thought_hash_from_cbor_object(obj: object) -> bytes:
    return hash_with_domain(DOMAIN_THOUGHT_CONTEXT, canonical_cbor(obj))


def merkle_node_hash(left: bytes, right: bytes) -> bytes:
    return blake3(DOMAIN_MERKLE_NODE + left + right).digest(length=32)


def merkle_root(ordered_hashes: Sequence[bytes]) -> bytes:
    """
    Build a binary Merkle root.

    Rules:
    - empty sequence is invalid
    - single element root == that element
    - odd level duplicates the last element
    """
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

    def to_cbor_obj(self) -> dict[int, object]:
        obj: dict[int, object] = {
            1: 1,
            2: self.root_type,
            3: self.root_hash,
            8: self.status,
            9: self.child_count,
            10: self.manifest_hash,
        }
        if self.tick_id is not None:
            obj[4] = self.tick_id
        if self.tick_start_ns is not None:
            obj[5] = self.tick_start_ns
        if self.tick_width_ns is not None:
            obj[6] = self.tick_width_ns
        if self.bucket_id is not None:
            obj[7] = self.bucket_id
        if self.previous_root_hash is not None:
            obj[11] = self.previous_root_hash
        if self.amendment_of_hash is not None:
            obj[12] = self.amendment_of_hash
        if self.labels:
            obj[14] = self.labels
        return obj


def event_sort_key(e: EventIndexRow) -> tuple[int, str, str, bytes]:
    return (e.event_time_ns, e.device_id, e.event_id, e.event_hash)


def manifest_hash(member_hashes: Sequence[bytes]) -> bytes:
    """
    Hash the ordered member list as a compact manifest object.
    This is not the Merkle root; it is a separate content-addressed manifest hash.
    """
    manifest_obj = {
        1: 1,
        2: list(member_hashes),
        3: len(member_hashes),
    }
    return hash_with_domain(b"mica:object:manifest:v1", canonical_cbor(manifest_obj))


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

        ordered = sorted(
            bucket_roots,
            key=lambda r: (
                r.bucket_id or "",
                r.root_hash,
            ),
        )
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

    def build_amendment_root(
        self,
        tick_id: int,
        original_root_hash: bytes,
        late_event_hashes: Sequence[bytes],
        reason_code: str,
        amendment_time_ns: int,
    ) -> RootRecord:
        if not late_event_hashes:
            raise ValueError("amendment root requires at least one late event hash")
        ordered = sorted(late_event_hashes)
        late_root = merkle_root(ordered)
        payload = {
            1: 1,
            2: original_root_hash,
            3: late_root,
            4: reason_code,
            5: amendment_time_ns,
        }
        root_hash = hash_with_domain(DOMAIN_AMENDMENT_ROOT, canonical_cbor(payload))
        return RootRecord(
            root_type="amendment",
            root_hash=root_hash,
            tick_id=tick_id,
            tick_start_ns=tick_id * self.tick_width_ns,
            tick_width_ns=self.tick_width_ns,
            bucket_id=None,
            status="amendment",
            child_count=len(ordered),
            manifest_hash=manifest_hash(ordered),
            amendment_of_hash=original_root_hash,
            labels={"reason_code": reason_code},
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
    ) -> tuple[bytes, dict[int, object]]:
        thought_obj: dict[int, object] = {
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
    """
    Build a Merkle proof for a target leaf from an already ordered list.

    Returns a list of tuples:
    - ("left", sibling_hash)  means sibling is on the left
    - ("right", sibling_hash) means sibling is on the right
    """
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

        is_right_node = (index % 2 == 1)
        sibling_index = index - 1 if is_right_node else index + 1
        sibling_hash = level[sibling_index]
        proof.append(("left" if is_right_node else "right", sibling_hash))

        next_level: list[bytes] = []
        for i in range(0, len(level), 2):
            next_level.append(merkle_node_hash(level[i], level[i + 1]))

        index //= 2
        level = next_level

    return proof


if __name__ == "__main__":
    # Minimal deterministic demo
    e1 = EventIndexRow(bytes.fromhex("00" * 32), 1_000_000_001, "devA", "evt-1", "8928308280fffff")
    e2 = EventIndexRow(bytes.fromhex("11" * 32), 1_000_000_010, "devB", "evt-2", "8928308280fffff")
    e3 = EventIndexRow(bytes.fromhex("22" * 32), 1_000_000_020, "devC", "evt-3", "8928308281bffff")

    erb = EventRootBuilder(tick_width_ns=1_000_000_000)
    temporal = erb.build_temporal_root(tick_id=1, events=[e1, e2, e3], status="provisional")
    spatial_buckets = erb.build_spatial_bucket_roots(tick_id=1, events=[e1, e2, e3], status="provisional")
    spatial = erb.build_spatial_root(tick_id=1, bucket_roots=spatial_buckets, status="provisional")
    event_root = erb.build_event_root(tick_id=1, temporal_root=temporal, spatial_root=spatial, status="provisional")

    srb = SnapshotRootBuilder()
    self_root = srb.build_slot_root(
        root_type="self",
        tick_id=1,
        tick_width_ns=1_000_000_000,
        slot_hashes={
            "identity": bytes.fromhex("33" * 32),
            "persona": bytes.fromhex("44" * 32),
            "policy": bytes.fromhex("55" * 32),
            "service_health": bytes.fromhex("66" * 32),
        },
    )
    world_root = srb.build_slot_root(
        root_type="world",
        tick_id=1,
        tick_width_ns=1_000_000_000,
        slot_hashes={
            "device_registry": bytes.fromhex("77" * 32),
            "crep_summary": bytes.fromhex("88" * 32),
            "environment_feeds": bytes.fromhex("99" * 32),
        },
    )

    trb = ThoughtRootBuilder()
    thought_hash, thought_obj = trb.build_thought_root(
        tick_id=1,
        thought_time_ns=1_000_000_500,
        actor_id="MICA",
        self_root_hash=self_root.root_hash,
        world_root_hash=world_root.root_hash,
        event_root_hash=event_root.root_hash,
    )

    print("temporal_root =", hex32(temporal.root_hash))
    print("spatial_root  =", hex32(spatial.root_hash))
    print("event_root    =", hex32(event_root.root_hash))
    print("self_root     =", hex32(self_root.root_hash))
    print("world_root    =", hex32(world_root.root_hash))
    print("thought_root  =", hex32(thought_hash))
    print("thought_obj_keys =", sorted(thought_obj.keys()))
