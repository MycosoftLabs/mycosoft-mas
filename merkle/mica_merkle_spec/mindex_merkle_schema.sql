-- MICA / MINDEX Merkleized Cognition Ledger v1
-- PostgreSQL schema for immutable objects, event indexes, Merkle roots, and thought lineage.
--
-- Notes:
-- - Hashing is done in the application / builder layer using BLAKE3-256.
-- - PostgreSQL stores object bytes, extracted index columns, and root membership.
-- - PostGIS is used for point queries. H3 cell IDs are stored as text.

BEGIN;

CREATE SCHEMA IF NOT EXISTS mica;

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE DOMAIN mica.hash32 AS bytea
  CHECK (octet_length(VALUE) = 32);

CREATE TABLE IF NOT EXISTS mica.ca_object (
  object_hash        mica.hash32 PRIMARY KEY,
  codec              text NOT NULL, -- dag-cbor|protobuf|raw
  object_type        text NOT NULL, -- event|self_snapshot|world_snapshot|root_record|thought_context|claim|receipt|blob
  size_bytes         integer NOT NULL CHECK (size_bytes >= 0),
  body_cbor          bytea,
  body_pb            bytea,
  created_at         timestamptz NOT NULL DEFAULT now(),
  created_by         text,
  schema_name        text,
  compression        text,
  encryption_scope   text,
  labels             jsonb NOT NULL DEFAULT '{}'::jsonb,
  CHECK (body_cbor IS NOT NULL OR body_pb IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS ca_object_object_type_idx ON mica.ca_object (object_type);
CREATE INDEX IF NOT EXISTS ca_object_created_at_idx  ON mica.ca_object (created_at);
CREATE INDEX IF NOT EXISTS ca_object_labels_gin      ON mica.ca_object USING gin (labels);

CREATE TABLE IF NOT EXISTS mica.event_object (
  event_hash             mica.hash32 PRIMARY KEY REFERENCES mica.ca_object(object_hash) ON DELETE RESTRICT,
  schema_version         integer NOT NULL DEFAULT 1,
  event_id               text NOT NULL,
  kind                   text NOT NULL,
  device_id              text NOT NULL,
  producer               text,
  capability_id          text,
  measurement_class      text,
  event_time             timestamptz NOT NULL,
  ingest_time            timestamptz NOT NULL,
  event_time_ns          bigint NOT NULL,
  ingest_time_ns         bigint NOT NULL,
  tick_width_ns          bigint NOT NULL CHECK (tick_width_ns > 0),
  tick_id                bigint NOT NULL,
  logical_counter        bigint,
  clock_domain           text,
  lat                    double precision,
  lon                    double precision,
  alt_m                  double precision,
  accuracy_m             double precision,
  h3_cell                text,
  geom                   geography(Point, 4326),
  raw_payload_hash       mica.hash32,
  provenance_parent_hashes mica.hash32[] NOT NULL DEFAULT ARRAY[]::bytea[],
  labels                 jsonb NOT NULL DEFAULT '{}'::jsonb,
  fields                 jsonb NOT NULL DEFAULT '[]'::jsonb,
  features               jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at             timestamptz NOT NULL DEFAULT now(),
  UNIQUE (device_id, event_id),
  CHECK ((lat IS NULL AND lon IS NULL AND geom IS NULL)
      OR (lat IS NOT NULL AND lon IS NOT NULL AND geom IS NOT NULL)),
  CHECK (event_time_ns >= 0),
  CHECK (ingest_time_ns >= 0)
);

CREATE INDEX IF NOT EXISTS event_object_event_time_idx   ON mica.event_object (event_time);
CREATE INDEX IF NOT EXISTS event_object_event_time_ns_idx ON mica.event_object (event_time_ns);
CREATE INDEX IF NOT EXISTS event_object_tick_id_idx      ON mica.event_object (tick_id);
CREATE INDEX IF NOT EXISTS event_object_device_id_idx    ON mica.event_object (device_id);
CREATE INDEX IF NOT EXISTS event_object_kind_idx         ON mica.event_object (kind);
CREATE INDEX IF NOT EXISTS event_object_measurement_idx  ON mica.event_object (measurement_class);
CREATE INDEX IF NOT EXISTS event_object_h3_tick_idx      ON mica.event_object (h3_cell, tick_id);
CREATE INDEX IF NOT EXISTS event_object_labels_gin       ON mica.event_object USING gin (labels);
CREATE INDEX IF NOT EXISTS event_object_fields_gin       ON mica.event_object USING gin (fields jsonb_path_ops);
CREATE INDEX IF NOT EXISTS event_object_features_gin     ON mica.event_object USING gin (features jsonb_path_ops);
CREATE INDEX IF NOT EXISTS event_object_geom_gist        ON mica.event_object USING gist (geom);

CREATE TABLE IF NOT EXISTS mica.root_record (
  root_hash             mica.hash32 PRIMARY KEY REFERENCES mica.ca_object(object_hash) ON DELETE RESTRICT,
  root_type             text NOT NULL CHECK (
                           root_type IN (
                             'temporal',
                             'spatial_bucket',
                             'spatial',
                             'event',
                             'self',
                             'world',
                             'truth_mirror',
                             'thought',
                             'amendment'
                           )
                         ),
  tick_id               bigint,
  tick_start_ns         bigint,
  tick_width_ns         bigint,
  bucket_id             text,
  status                text NOT NULL CHECK (status IN ('open', 'provisional', 'final', 'amendment')),
  child_count           bigint NOT NULL DEFAULT 0 CHECK (child_count >= 0),
  manifest_hash         mica.hash32 REFERENCES mica.ca_object(object_hash) ON DELETE RESTRICT,
  previous_root_hash    mica.hash32 REFERENCES mica.root_record(root_hash) ON DELETE RESTRICT,
  amendment_of_hash     mica.hash32 REFERENCES mica.root_record(root_hash) ON DELETE RESTRICT,
  created_at            timestamptz NOT NULL DEFAULT now(),
  labels                jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS root_record_type_tick_idx ON mica.root_record (root_type, tick_id, status);
CREATE INDEX IF NOT EXISTS root_record_bucket_idx    ON mica.root_record (bucket_id);
CREATE INDEX IF NOT EXISTS root_record_created_idx   ON mica.root_record (created_at);
CREATE INDEX IF NOT EXISTS root_record_labels_gin    ON mica.root_record USING gin (labels);

CREATE TABLE IF NOT EXISTS mica.root_member (
  root_hash             mica.hash32 NOT NULL REFERENCES mica.root_record(root_hash) ON DELETE CASCADE,
  ordinal               bigint NOT NULL CHECK (ordinal >= 0),
  member_hash           mica.hash32 NOT NULL,
  member_type           text NOT NULL, -- event_leaf|bucket_root|component_hash|claim_hash|...
  key_text              text,
  PRIMARY KEY (root_hash, ordinal)
);

CREATE INDEX IF NOT EXISTS root_member_member_hash_idx ON mica.root_member (member_hash);
CREATE INDEX IF NOT EXISTS root_member_key_text_idx    ON mica.root_member (key_text);

CREATE TABLE IF NOT EXISTS mica.self_snapshot (
  snapshot_hash         mica.hash32 PRIMARY KEY REFERENCES mica.ca_object(object_hash) ON DELETE RESTRICT,
  snapshot_time         timestamptz NOT NULL,
  snapshot_time_ns      bigint NOT NULL,
  tick_id               bigint NOT NULL,
  actor_id              text NOT NULL,
  session_id            text,
  previous_snapshot_hash mica.hash32 REFERENCES mica.self_snapshot(snapshot_hash) ON DELETE RESTRICT,
  component_count       integer NOT NULL DEFAULT 0 CHECK (component_count >= 0),
  labels                jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS self_snapshot_tick_idx      ON mica.self_snapshot (tick_id);
CREATE INDEX IF NOT EXISTS self_snapshot_actor_idx     ON mica.self_snapshot (actor_id);
CREATE INDEX IF NOT EXISTS self_snapshot_created_idx   ON mica.self_snapshot (snapshot_time);

CREATE TABLE IF NOT EXISTS mica.self_snapshot_component (
  snapshot_hash         mica.hash32 NOT NULL REFERENCES mica.self_snapshot(snapshot_hash) ON DELETE CASCADE,
  slot                  text NOT NULL,
  component_hash        mica.hash32 NOT NULL REFERENCES mica.ca_object(object_hash) ON DELETE RESTRICT,
  component_type        text NOT NULL,
  component_name        text,
  labels                jsonb NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (snapshot_hash, slot)
);

CREATE INDEX IF NOT EXISTS self_snapshot_component_hash_idx ON mica.self_snapshot_component (component_hash);

CREATE TABLE IF NOT EXISTS mica.world_snapshot (
  snapshot_hash         mica.hash32 PRIMARY KEY REFERENCES mica.ca_object(object_hash) ON DELETE RESTRICT,
  snapshot_time         timestamptz NOT NULL,
  snapshot_time_ns      bigint NOT NULL,
  tick_id               bigint NOT NULL,
  source_id             text NOT NULL,
  previous_snapshot_hash mica.hash32 REFERENCES mica.world_snapshot(snapshot_hash) ON DELETE RESTRICT,
  component_count       integer NOT NULL DEFAULT 0 CHECK (component_count >= 0),
  labels                jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS world_snapshot_tick_idx      ON mica.world_snapshot (tick_id);
CREATE INDEX IF NOT EXISTS world_snapshot_source_idx    ON mica.world_snapshot (source_id);
CREATE INDEX IF NOT EXISTS world_snapshot_created_idx   ON mica.world_snapshot (snapshot_time);

CREATE TABLE IF NOT EXISTS mica.world_snapshot_component (
  snapshot_hash         mica.hash32 NOT NULL REFERENCES mica.world_snapshot(snapshot_hash) ON DELETE CASCADE,
  slot                  text NOT NULL,
  component_hash        mica.hash32 NOT NULL REFERENCES mica.ca_object(object_hash) ON DELETE RESTRICT,
  component_type        text NOT NULL,
  component_name        text,
  labels                jsonb NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (snapshot_hash, slot)
);

CREATE INDEX IF NOT EXISTS world_snapshot_component_hash_idx ON mica.world_snapshot_component (component_hash);

CREATE TABLE IF NOT EXISTS mica.claim_object (
  claim_hash            mica.hash32 PRIMARY KEY REFERENCES mica.ca_object(object_hash) ON DELETE RESTRICT,
  claim_time            timestamptz NOT NULL,
  claim_time_ns         bigint NOT NULL,
  tick_id               bigint NOT NULL,
  channel               text NOT NULL,
  spoken_text           text NOT NULL,
  confidence            real NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
  interrupted           boolean NOT NULL DEFAULT false,
  thought_root_hash     mica.hash32 NOT NULL REFERENCES mica.root_record(root_hash) ON DELETE RESTRICT,
  stale_after_ns        bigint,
  evidence_hashes       mica.hash32[] NOT NULL DEFAULT ARRAY[]::bytea[],
  labels                jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS claim_object_tick_idx         ON mica.claim_object (tick_id);
CREATE INDEX IF NOT EXISTS claim_object_thought_idx      ON mica.claim_object (thought_root_hash);
CREATE INDEX IF NOT EXISTS claim_object_channel_idx      ON mica.claim_object (channel);

CREATE TABLE IF NOT EXISTS mica.thought_context (
  thought_root_hash         mica.hash32 PRIMARY KEY REFERENCES mica.root_record(root_hash) ON DELETE RESTRICT,
  tick_id                   bigint NOT NULL,
  thought_time              timestamptz NOT NULL,
  thought_time_ns           bigint NOT NULL,
  actor_id                  text NOT NULL,
  session_id                text,
  self_root_hash            mica.hash32 NOT NULL REFERENCES mica.root_record(root_hash) ON DELETE RESTRICT,
  world_root_hash           mica.hash32 NOT NULL REFERENCES mica.root_record(root_hash) ON DELETE RESTRICT,
  event_root_hash           mica.hash32 NOT NULL REFERENCES mica.root_record(root_hash) ON DELETE RESTRICT,
  truth_mirror_root_hash    mica.hash32 REFERENCES mica.root_record(root_hash) ON DELETE RESTRICT,
  previous_thought_root_hash mica.hash32 REFERENCES mica.thought_context(thought_root_hash) ON DELETE RESTRICT,
  policy_root_hash          mica.hash32 REFERENCES mica.ca_object(object_hash) ON DELETE RESTRICT,
  evidence_root_hashes      mica.hash32[] NOT NULL DEFAULT ARRAY[]::bytea[],
  status                    text NOT NULL CHECK (status IN ('provisional', 'final', 'amendment')),
  labels                    jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at                timestamptz NOT NULL DEFAULT now(),
  UNIQUE (actor_id, tick_id, status)
);

CREATE INDEX IF NOT EXISTS thought_context_tick_idx   ON mica.thought_context (tick_id);
CREATE INDEX IF NOT EXISTS thought_context_actor_idx  ON mica.thought_context (actor_id);
CREATE INDEX IF NOT EXISTS thought_context_time_idx   ON mica.thought_context (thought_time);

CREATE TABLE IF NOT EXISTS mica.action_receipt (
  receipt_hash             mica.hash32 PRIMARY KEY REFERENCES mica.ca_object(object_hash) ON DELETE RESTRICT,
  action_time              timestamptz NOT NULL,
  action_time_ns           bigint NOT NULL,
  thought_root_hash        mica.hash32 NOT NULL REFERENCES mica.thought_context(thought_root_hash) ON DELETE RESTRICT,
  tool_name                text NOT NULL,
  args_hash                mica.hash32 REFERENCES mica.ca_object(object_hash) ON DELETE RESTRICT,
  result_hash              mica.hash32 REFERENCES mica.ca_object(object_hash) ON DELETE RESTRICT,
  post_self_root_hash      mica.hash32 REFERENCES mica.root_record(root_hash) ON DELETE RESTRICT,
  post_world_root_hash     mica.hash32 REFERENCES mica.root_record(root_hash) ON DELETE RESTRICT,
  status                   text NOT NULL,
  latency_ms               integer CHECK (latency_ms >= 0),
  labels                   jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS action_receipt_thought_idx ON mica.action_receipt (thought_root_hash);
CREATE INDEX IF NOT EXISTS action_receipt_tool_idx    ON mica.action_receipt (tool_name);
CREATE INDEX IF NOT EXISTS action_receipt_time_idx    ON mica.action_receipt (action_time);

CREATE TABLE IF NOT EXISTS mica.watermark_state (
  stream_id              text PRIMARY KEY,
  tick_width_ns          bigint NOT NULL CHECK (tick_width_ns > 0),
  max_lateness_ns        bigint NOT NULL CHECK (max_lateness_ns >= 0),
  max_seen_event_time_ns bigint NOT NULL DEFAULT 0,
  watermark_ns           bigint NOT NULL DEFAULT 0,
  last_final_tick_id     bigint NOT NULL DEFAULT -1,
  updated_at             timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mica.mutable_head (
  head_name              text PRIMARY KEY,
  object_hash            mica.hash32 NOT NULL REFERENCES mica.ca_object(object_hash) ON DELETE RESTRICT,
  updated_at             timestamptz NOT NULL DEFAULT now(),
  labels                 jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS mutable_head_updated_idx ON mica.mutable_head (updated_at);

CREATE OR REPLACE VIEW mica.latest_thought AS
SELECT tc.*
FROM mica.thought_context tc
JOIN (
  SELECT actor_id, max(thought_time_ns) AS max_time
  FROM mica.thought_context
  GROUP BY actor_id
) t
  ON t.actor_id = tc.actor_id
 AND t.max_time = tc.thought_time_ns;

CREATE OR REPLACE VIEW mica.latest_final_event_root AS
SELECT rr.*
FROM mica.root_record rr
WHERE rr.root_type = 'event'
  AND rr.status = 'final'
ORDER BY rr.tick_id DESC NULLS LAST
LIMIT 1;

COMMENT ON TABLE mica.ca_object IS
'Immutable content-addressed object storage. Canonical hash is computed in application layer over deterministic CBOR.';
COMMENT ON TABLE mica.event_object IS
'Extracted event index for time, space, device, and measurement queries. Event body remains immutable in ca_object.';
COMMENT ON TABLE mica.root_record IS
'Metadata for Merkle roots (temporal, spatial, event, self, world, truth, thought).';
COMMENT ON TABLE mica.root_member IS
'Deterministic ordered members for each root. Enough to regenerate inclusion proofs.';
COMMENT ON TABLE mica.thought_context IS
'Root lineage that MICA must bind before reasoning, planning, or action.';
COMMENT ON TABLE mica.action_receipt IS
'Action and tool execution lineage back to thought roots and forward to post-action roots.';

COMMIT;
