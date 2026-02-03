-- NatureOS Memory Integration Views - February 3, 2026

CREATE OR REPLACE VIEW memory.device_memory AS SELECT e.id as memory_id, e.namespace, e.key, e.value, e.source, e.confidence, e.access_count, e.created_at, e.updated_at, (e.value->>'device_id')::UUID as device_id, e.value->>'device_type' as device_type, e.value->>'status' as device_status FROM memory.entries e WHERE e.scope = 'device';

CREATE TABLE IF NOT EXISTS memory.telemetry_snapshots (
    id SERIAL PRIMARY KEY,
    device_id UUID NOT NULL,
    device_type VARCHAR(50),
    readings JSONB NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    sample_count INTEGER DEFAULT 0,
    stats JSONB DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_telemetry_snapshots_device ON memory.telemetry_snapshots(device_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_snapshots_window ON memory.telemetry_snapshots(window_start DESC);

CREATE TABLE IF NOT EXISTS memory.device_state_history (
    id SERIAL PRIMARY KEY,
    device_id UUID NOT NULL,
    status VARCHAR(20),
    firmware_version VARCHAR(50),
    config JSONB,
    calibration_data JSONB,
    health_score FLOAT,
    uptime_seconds BIGINT,
    error_count INTEGER DEFAULT 0,
    changed_fields TEXT[],
    change_reason VARCHAR(100),
    captured_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_device_state_device ON memory.device_state_history(device_id);
CREATE INDEX IF NOT EXISTS idx_device_state_captured ON memory.device_state_history(captured_at DESC);

CREATE OR REPLACE FUNCTION memory.store_telemetry_snapshot(p_device_id UUID, p_device_type VARCHAR, p_readings JSONB, p_window_minutes INTEGER DEFAULT 5) RETURNS INTEGER AS $$ DECLARE v_snapshot_id INTEGER; v_window_start TIMESTAMPTZ; v_window_end TIMESTAMPTZ; BEGIN v_window_end = NOW(); v_window_start = v_window_end - (p_window_minutes || ' minutes')::INTERVAL; INSERT INTO memory.telemetry_snapshots (device_id, device_type, readings, window_start, window_end, sample_count) VALUES (p_device_id, p_device_type, p_readings, v_window_start, v_window_end, 1) RETURNING id INTO v_snapshot_id; INSERT INTO memory.entries (scope, namespace, key, value, source) VALUES ('device', 'telemetry:' || p_device_id::text, 'snapshot:' || v_window_end::text, jsonb_build_object('device_id', p_device_id, 'device_type', p_device_type, 'readings', p_readings, 'window_start', v_window_start, 'window_end', v_window_end), 'natureos') ON CONFLICT (scope, namespace, key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW(); RETURN v_snapshot_id; END; $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION memory.store_environmental_event(p_event_type VARCHAR, p_severity VARCHAR, p_device_id UUID, p_location JSONB, p_data JSONB) RETURNS UUID AS $$ DECLARE v_event_id UUID; v_entry_id UUID; BEGIN v_event_id = gen_random_uuid(); INSERT INTO memory.entries (scope, namespace, key, value, source, confidence) VALUES ('system', 'natureos:events:' || p_event_type, v_event_id::text, jsonb_build_object('event_id', v_event_id, 'event_type', p_event_type, 'severity', p_severity, 'device_id', p_device_id, 'location', p_location, 'data', p_data, 'detected_at', NOW()), 'natureos', CASE p_severity WHEN 'critical' THEN 1.0 WHEN 'warning' THEN 0.8 WHEN 'info' THEN 0.6 ELSE 0.5 END) RETURNING id INTO v_entry_id; RETURN v_event_id; END; $$ LANGUAGE plpgsql;

CREATE OR REPLACE VIEW memory.environmental_events AS SELECT e.id as memory_id, e.namespace, e.key, e.value->>'event_type' as event_type, e.value->>'severity' as severity, (e.value->>'device_id')::UUID as source_device_id, e.value->'location' as location, e.value->'data' as event_data, e.confidence, e.created_at as detected_at FROM memory.entries e WHERE e.scope = 'system' AND e.namespace LIKE 'natureos:events:%';

COMMENT ON VIEW memory.device_memory IS 'Device entries from memory system';
COMMENT ON TABLE memory.telemetry_snapshots IS 'Aggregated telemetry snapshots';
