"""
MICA/MYCA Merkleized Cognition Ledger.

Content-addressed event/object store with Merkle DAG roots:
- TemporalRoot, SpatialRoot, EventRoot (event-space-time)
- SelfStateRoot (MYCA internal state)
- WorldStateRoot (external world model)
- ThoughtPlanRoot (super-root for reasoning)
- TruthMirrorRoot (spoken/UI claims)

See merkle/mica_merkle_spec/README.md for full architecture.
"""

from mycosoft_mas.merkle.root_builder import (
    EventIndexRow,
    EventRootBuilder,
    RootRecord,
    SnapshotRootBuilder,
    ThoughtRootBuilder,
    build_inclusion_proof,
    canonical_cbor,
    hex32,
    leaf_hash_from_cbor_object,
    merkle_root,
    thought_hash_from_cbor_object,
    world_slot_hash,
)

__all__ = [
    "EventIndexRow",
    "EventRootBuilder",
    "RootRecord",
    "SnapshotRootBuilder",
    "ThoughtRootBuilder",
    "build_inclusion_proof",
    "canonical_cbor",
    "hex32",
    "leaf_hash_from_cbor_object",
    "merkle_root",
    "thought_hash_from_cbor_object",
    "world_slot_hash",
]
