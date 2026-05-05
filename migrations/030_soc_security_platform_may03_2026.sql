-- SOC / Security platform tables — May 03, 2026
-- Target: MINDEX Postgres (same database as MAS MINDEX_DATABASE_URL / palace pool)
-- Schema: soc_ops (isolated from public Supabase tables)

CREATE SCHEMA IF NOT EXISTS soc_ops;

-- ---------------------------------------------------------------------------
-- Device inventory (UniFi, ARP, MQTT, HTTP probe, heartbeat, SSH probe)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS soc_ops.device_inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mac TEXT,
    ip INET,
    hostname TEXT,
    board_type TEXT,
    device_id TEXT,
    source TEXT NOT NULL CHECK (source IN (
        'unifi', 'arp', 'mqtt', 'http_probe', 'heartbeat', 'ssh_probe', 'reconciled'
    )),
    classified_as TEXT,
    status TEXT NOT NULL DEFAULT 'unknown',
    capabilities JSONB NOT NULL DEFAULT '{}'::jsonb,
    raw JSONB NOT NULL DEFAULT '{}'::jsonb,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Partial uniques so ON CONFLICT works and multiple NULL macs are allowed
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_inventory_mac_unique
    ON soc_ops.device_inventory (mac)
    WHERE mac IS NOT NULL AND length(trim(mac)) > 0;

CREATE UNIQUE INDEX IF NOT EXISTS idx_device_inventory_ip_unique
    ON soc_ops.device_inventory (ip)
    WHERE ip IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_device_inventory_last_seen
    ON soc_ops.device_inventory (last_seen DESC);

CREATE INDEX IF NOT EXISTS idx_device_inventory_classified
    ON soc_ops.device_inventory (classified_as);

-- ---------------------------------------------------------------------------
-- Security incidents (canonical MAS / SOC)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS soc_ops.security_incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    severity TEXT NOT NULL CHECK (severity IN (
        'info', 'low', 'medium', 'high', 'critical'
    )),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN (
        'open', 'investigating', 'contained', 'resolved', 'closed', 'acknowledged'
    )),
    source TEXT,
    kind TEXT,
    source_ip TEXT,
    host TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    assigned_to TEXT,
    tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    timeline JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ack_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    chain_block_id BIGINT
);

CREATE INDEX IF NOT EXISTS idx_security_incidents_status
    ON soc_ops.security_incidents (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_security_incidents_severity
    ON soc_ops.security_incidents (severity, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_security_incidents_source_ip
    ON soc_ops.security_incidents (source_ip)
    WHERE source_ip IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Tamper-evident incident chain (append-only)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS soc_ops.incident_chain (
    id BIGSERIAL PRIMARY KEY,
    incident_id UUID REFERENCES soc_ops.security_incidents(id) ON DELETE CASCADE,
    sequence_number INT NOT NULL,
    prev_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (incident_id, sequence_number)
);

CREATE INDEX IF NOT EXISTS idx_incident_chain_incident
    ON soc_ops.incident_chain (incident_id, sequence_number);

-- ---------------------------------------------------------------------------
-- Red team runs and findings
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS soc_ops.redteam_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    layer INT NOT NULL CHECK (layer IN (1, 2, 3)),
    scope TEXT NOT NULL,
    tool TEXT NOT NULL DEFAULT '',
    params JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN (
        'running', 'completed', 'failed', 'cancelled'
    )),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    summary TEXT,
    raw_log TEXT
);

CREATE TABLE IF NOT EXISTS soc_ops.redteam_findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES soc_ops.redteam_runs(id) ON DELETE CASCADE,
    severity TEXT NOT NULL CHECK (severity IN (
        'info', 'low', 'medium', 'high', 'critical'
    )),
    control_id TEXT,
    title TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'accepted', 'false_positive', 'remediated')),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_redteam_findings_run
    ON soc_ops.redteam_findings (run_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- NIST 800-171 control state + versioned compliance documents
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS soc_ops.compliance_controls (
    control_id TEXT PRIMARY KEY,
    framework TEXT NOT NULL DEFAULT 'NIST_800_171',
    family TEXT,
    title TEXT,
    implementation_state TEXT NOT NULL DEFAULT 'unknown' CHECK (implementation_state IN (
        'implemented', 'partial', 'planned', 'not_applicable', 'unknown'
    )),
    evidence_uri TEXT,
    last_verified_at TIMESTAMPTZ,
    state_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS soc_ops.compliance_docs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_type TEXT NOT NULL CHECK (doc_type IN ('SSP', 'POAM', 'policy', 'attachment')),
    version INT NOT NULL DEFAULT 1,
    title TEXT NOT NULL,
    body_md TEXT NOT NULL DEFAULT '',
    model_versions JSONB NOT NULL DEFAULT '{}'::jsonb,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_by TEXT,
    superseded_by UUID REFERENCES soc_ops.compliance_docs(id)
);

CREATE INDEX IF NOT EXISTS idx_compliance_docs_type_version
    ON soc_ops.compliance_docs (doc_type, version DESC, generated_at DESC);

COMMENT ON SCHEMA soc_ops IS 'MAS SOC: devices, incidents, red team, compliance — May 03, 2026';
