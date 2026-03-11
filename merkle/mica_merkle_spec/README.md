# MICA / MINDEX Merkleized Cognition Ledger v1

## Purpose

This specification turns MICA's "self + world + all spatiotemporal events" concept into a concrete, deterministic, content-addressed architecture.

The design goal is:

- every incoming event is immutable and hash-addressed
- every event is indexed by time and space without duplication of the event body
- MICA maintains separate cryptographic roots for self-state, world-state, and event-space-time
- every decision, plan, action, and spoken claim can point back to the exact roots it was grounded on

The result is a **Merkleized cognition ledger** rather than one giant tree.

---

## Core design invariants

1. **Event bodies exist exactly once.**
   Time buckets and space buckets reference the same event leaf hash.

2. **Hashing never uses JSON text.**
   Hashing uses deterministic CBOR only.

3. **Transport and hashing are separate concerns.**
   Protobuf is used for wire transport and typed APIs.
   Deterministic CBOR is used for canonical hashing.

4. **All Merkle roots are immutable.**
   Mutable heads point at the newest roots.

5. **Late data does not rewrite finalized roots.**
   It creates amendment roots.

6. **Ordering is deterministic by rule, not by arrival order.**

7. **Every action references a thought root.**
   MICA does not act "free-floating"; it acts from a rooted state.

---

## Object model

### 1. Event leaf object

An event leaf represents a single normalized incoming observation, pattern, command result, status update, or internal state event.

Minimum required fields:

- `event_id`
- `kind`
- `device_id`
- `event_time_ns`
- `ingest_time_ns`
- `tick_width_ns`
- `tick_id`
- `lat_e7`
- `lon_e7`
- `h3_cell`
- `measurement_class`
- `fields`
- `features`
- `provenance`

The canonical event is encoded to deterministic CBOR and hashed into `event_hash`.

### 2. Self snapshot object

A self snapshot is a compact immutable object that points to component hashes for:

- agent graph
- active tasks
- tool registry
- memory heads
- file graph
- service health
- persona/policy
- safety state

It is hashed into `self_snapshot_hash`, and then Merkleized into `self_root`.

### 3. World snapshot object

A world snapshot is a compact immutable object that points to component hashes for:

- device summaries
- CREP summaries
- NLM outputs
- environmental feeds
- simulator state
- anomaly summaries
- graph / map summaries
- active alerts

It is hashed into `world_snapshot_hash`, and then Merkleized into `world_root`.

### 4. Root record object

Every built root also has an immutable root record object that contains:

- root type
- tick metadata
- finalization status
- member count
- manifest hash
- parent/amendment pointers

### 5. Thought context object

This binds together the roots that must exist before reasoning:

- `self_root`
- `world_root`
- `event_root`
- optional `truth_mirror_root`
- optional `policy_root`
- optional `previous_thought_root`

It is hashed into `thought_root`.

---

## Root hierarchy

### Per event

```text
event_object --deterministic CBOR--> event_hash
```

### Per tick

For every tick `t`:

```text
TemporalRoot(t) = Merkle(sorted(event_hash for all events in tick t))

SpatialBucketRoot(t, cell) = Merkle(sorted(event_hash for all events in tick t and h3_cell = cell))

SpatialRoot(t) = Merkle(sorted(hash(SpatialBucketRoot(t, cell)) for all cells active in tick t))

EventRoot(t) = H("mica:root:event:v1" || TemporalRoot(t) || SpatialRoot(t))
```

### Per self/world snapshot window

```text
SelfRoot(t)  = Merkle(fixed-slot hashes for MICA internal state at tick t)
WorldRoot(t) = Merkle(fixed-slot hashes for external world state at tick t)
```

### Per cognition tick

```text
ThoughtRoot(t) = H(
  "mica:root:thought:v1" ||
  tick_id ||
  thought_time_ns ||
  SelfRoot(t) ||
  WorldRoot(t) ||
  EventRoot(t) ||
  TruthMirrorRoot(t)? ||
  PolicyRoot? ||
  PreviousThoughtRoot?
)
```

---

## Exact hash rules

## Algorithm

Default algorithm for v1:

- **BLAKE3-256**
- output size: 32 bytes
- stored as raw `BYTEA` in PostgreSQL
- rendered as lowercase hex in APIs when needed

## Domain separation

Every hash uses a domain prefix.

### Leaf hash

```text
leaf_hash = BLAKE3(
  utf8("mica:leaf:event:v1") ||
  canonical_cbor(event_object)
)
```

### Snapshot object hash

```text
snapshot_hash = BLAKE3(
  utf8("mica:object:snapshot:v1") ||
  canonical_cbor(snapshot_object)
)
```

### Merkle node hash

```text
node_hash = BLAKE3(
  utf8("mica:node:v1") ||
  left_child_hash ||
  right_child_hash
)
```

### Root record hash

```text
root_record_hash = BLAKE3(
  utf8("mica:object:root_record:v1") ||
  canonical_cbor(root_record_object)
)
```

### Thought context hash

```text
thought_hash = BLAKE3(
  utf8("mica:object:thought_context:v1") ||
  canonical_cbor(thought_context_object)
)
```

## Merkle tree construction

- Leaves are supplied in **deterministic sorted order**.
- Trees are built bottom-up.
- If a level has an odd number of nodes, the last node is duplicated.
- Empty bucket root is not a null root object. Empty buckets do not exist.
- A single-member tree root is the member hash itself.

---

## Deterministic ordering rules

### Event leaves in temporal and spatial buckets

Sort ascending by:

1. `event_time_ns`
2. `device_id`
3. `event_id`
4. `event_hash` lexicographically

This preserves deterministic replay while preventing ingestion-order drift.

### Spatial bucket roots inside a spatial root

Sort ascending by:

1. `h3_cell`
2. `bucket_root_hash`

### Self and world snapshot slots

Do **not** sort self/world slots by hash.

Use a **fixed slot order** so semantic meaning is stable:

#### Self slot order

1. `identity`
2. `persona`
3. `policy`
4. `safety`
5. `agent_graph`
6. `active_tasks`
7. `tool_registry`
8. `memory_heads`
9. `filesystem_heads`
10. `service_health`
11. `network_status`
12. `open_sessions`

#### World slot order

1. `device_registry`
2. `device_health`
3. `crep_summary`
4. `nlm_summary`
5. `earth_sim_summary`
6. `environment_feeds`
7. `forecast_state`
8. `anomaly_state`
9. `map_state`
10. `external_alerts`

---

## Time model

### Tick definition

A tick is a fixed-width window.

Default v1:

- `tick_width_ns = 1_000_000_000` (1 second)

Compute:

```text
tick_id       = floor(event_time_ns / tick_width_ns)
tick_start_ns = tick_id * tick_width_ns
tick_end_ns   = tick_start_ns + tick_width_ns
```

### Watermark and finalization

Every stream or shard maintains:

- `max_seen_event_time_ns`
- `watermark_ns = max_seen_event_time_ns - max_lateness_ns`

Default v1:

- `max_lateness_ns = 30_000_000_000` (30 seconds)

States:

- `open`
- `provisional`
- `final`
- `amendment`

Rule:

- when tick closes, provisional roots may be emitted immediately
- when watermark passes tick end, roots become final
- if a late event arrives after finalization, create an amendment root

### Amendment rule

```text
AmendmentRoot = H(
  "mica:root:amendment:v1" ||
  original_root_hash ||
  Merkle(sorted(late_event_hashes)) ||
  reason_code ||
  amendment_time_ns
)
```

---

## Space model

### Primary spatial index

Use **H3 cell IDs** for bucketization.

Store raw coordinates as:

- `lat_e7`
- `lon_e7`
- optional `alt_mm`

Store bucket cell as:

- `h3_cell` (text hex form)

Default v1 H3 resolution:

- `res = 9` for general event bucketization

Optional additional parent cells may be materialized for rollups:

- `h3_r5`
- `h3_r7`
- `h3_r9`
- `h3_r11`

### Why this shape

- event leaf stores exact coordinate
- bucket root groups by H3 cell
- spatial root groups the active cells for a tick

This avoids duplicating event objects while still supporting space proofs.

---

## Mutable heads

These are not Merkle objects. They are moving pointers.

Recommended heads:

- `HEAD/events/latest_final`
- `HEAD/events/latest_provisional`
- `HEAD/self/latest`
- `HEAD/world/latest`
- `HEAD/thought/latest`
- `HEAD/truth/latest`

Store heads in Redis or PostgreSQL for convenience, but treat them as pointers only.

---

## Truth mirror

If MICA speaks or displays a claim, create a claim object containing:

- spoken/display text hash
- evidence hashes
- thought root
- confidence
- stale_after_ns
- source channel
- interruption flag

Then Merkleize all claims spoken in a tick:

```text
TruthMirrorRoot(t) = Merkle(sorted(claim_hashes for tick t))
```

This gives a verifiable "what MICA said vs what MICA knew" trail.

---

## PostgreSQL architecture

PostgreSQL is not the Merkle engine itself. It is:

- the ledger metadata store
- the query index
- the membership/proof cache
- the mutable head store

The actual BLAKE3 hashing and Merkle construction should run in root-builder services.

Tables provided in `mindex_merkle_schema.sql` cover:

- content-addressed objects
- extracted event index
- root records
- root membership
- self/world snapshots
- thought contexts
- action receipts
- watermark state
- mutable heads

---

## Service boundaries

### 1. `mmp_ingest_gateway`

Responsibility:

- receive MMP / Mycorrhizae envelopes
- validate schema
- compute tick id and H3 cell
- canonicalize to CBOR
- hash to `event_hash`
- upsert content-addressed object
- insert event index row
- enqueue `event_hash` to root builders

Input:

- Protobuf `MMPEnvelope`

Output:

- stored `event_hash`
- event index row
- queue message for builders

### 2. `self_snapshot_builder`

Responsibility:

- collect current MICA internal state component hashes
- build self snapshot object
- hash snapshot
- build `SelfRoot(t)`

### 3. `world_snapshot_builder`

Responsibility:

- collect current external world component hashes
- build world snapshot object
- hash snapshot
- build `WorldRoot(t)`

### 4. `event_root_builder`

Responsibility:

- build temporal root
- build spatial bucket roots
- build spatial root
- build event root
- emit provisional/final/amendment root records

### 5. `thought_root_builder`

Responsibility:

- join `self_root`, `world_root`, `event_root`, optional `truth_mirror_root`
- build thought context object
- hash into `thought_root`
- publish thought root to cognition services

### 6. `proof_service`

Responsibility:

- produce inclusion proofs for:
  - event in temporal root
  - event in spatial bucket root
  - bucket root in spatial root
  - thought root lineage
  - spoken claim in truth mirror root

### 7. `anchor_writer`

Responsibility:

- roll daily or hourly digest
- anchor digest externally if desired
- never block local operation on external anchor availability

---

## Recommended pipeline

```text
device / ETL / FCI / CREP / Earth model
    -> MMP envelope
    -> ingest_gateway
    -> deterministic CBOR
    -> event_hash
    -> object store + event index
    -> temporal/spatial builders
    -> EventRoot(t)

MICA internal state
    -> self_snapshot_builder
    -> SelfRoot(t)

world summaries
    -> world_snapshot_builder
    -> WorldRoot(t)

claims / UI speech mirrors
    -> truth_mirror_builder
    -> TruthMirrorRoot(t)

ThoughtRoot(t)
    <- SelfRoot(t)
    <- WorldRoot(t)
    <- EventRoot(t)
    <- TruthMirrorRoot(t)?
```

---

## Action lineage

Every action should point backward and forward:

```text
ThoughtRoot -> IntentObject -> PlanObject -> ActionObject -> ReceiptObject
```

Minimum receipt fields:

- `thought_root_hash`
- `tool_name`
- `args_hash`
- `result_hash`
- `post_self_root_hash`
- `post_world_root_hash`
- `status`
- `latency_ms`

---

## Failure semantics

### Duplicate event

If the same canonical event body arrives twice:

- `event_hash` is identical
- content-addressed object insert is idempotent
- event index may reject duplicate `(device_id, event_id)`

### Missing geo

If no coordinate exists:

- `h3_cell = NULL`
- event enters temporal root
- event does not enter spatial bucket roots

### Missing event time

If no source event time exists:

- reject unless ingest policy allows fallback
- fallback policy may set `event_time_ns = ingest_time_ns` and mark `labels.time_source = "ingest_fallback"`

### Root builder outage

- ingestion still persists immutable events
- root builders replay from index and queue when restored

---

## Suggested rollout

### Phase 1
- event hashing
- event index
- temporal roots
- spatial bucket roots
- spatial root
- event root

### Phase 2
- self snapshots
- world snapshots
- thought roots

### Phase 3
- truth mirror roots
- action receipts
- proof API
- external anchoring

### Phase 4
- multi-resolution spatial rollups
- causal roots
- model-state roots
- public proof endpoints

---

## Non-negotiable implementation choices

1. Use **deterministic CBOR** for canonical hashing.
2. Use **BLAKE3-256** in the app layer.
3. Keep **event bodies immutable** and referenced from multiple trees.
4. Build **provisional + final + amendment** roots.
5. Require **thought_root** before plan/action/claim generation.
6. Keep **MAS live** and **MINDEX authoritative**.
7. Keep **truth mirror** linked to thought roots.

---

## Files in this bundle

- `mindex_merkle.proto`
- `mindex_merkle.cddl`
- `mindex_merkle_schema.sql`
- `root_builder.py`

