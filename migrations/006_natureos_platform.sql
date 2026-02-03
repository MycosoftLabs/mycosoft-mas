-- MYCA Autonomous Scientific Architecture
-- Migration 006: NatureOS Platform Schema
-- Created: February 3, 2026

CREATE SCHEMA IF NOT EXISTS natureos;

CREATE TABLE IF NOT EXISTS natureos.devices (
    device_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_type VARCHAR(50) NOT NULL,
    device_class VARCHAR(50),
    hardware_version VARCHAR(20),
    firmware_version VARCHAR(20),
    status VARCHAR(20) DEFAULT ''offline'',
    location GEOGRAPHY(POINT, 4326),
    location_name VARCHAR(255),
    capabilities JSONB DEFAULT ''{}'',
    config JSONB DEFAULT ''{}'',
    calibration_data JSONB DEFAULT ''{}'',
    mesh_network_id UUID,
    last_telemetry TIMESTAMPTZ,
    last_heartbeat TIMESTAMPTZ,
    registered_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS natureos.commands (
    command_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID REFERENCES natureos.devices(device_id) ON DELETE CASCADE,
    command_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL DEFAULT ''{}'',
    priority INTEGER DEFAULT 5,
    status VARCHAR(20) DEFAULT ''pending'',
    response JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    executed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    timeout_seconds INTEGER DEFAULT 30
);

CREATE TABLE IF NOT EXISTS natureos.telemetry (
    id BIGSERIAL PRIMARY KEY,
    device_id UUID REFERENCES natureos.devices(device_id) ON DELETE CASCADE,
    sensor_type VARCHAR(50) NOT NULL,
    reading JSONB NOT NULL,
    unit VARCHAR(20),
    quality_score FLOAT DEFAULT 1.0,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS natureos.environmental_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    source_device_id UUID REFERENCES natureos.devices(device_id),
    location GEOGRAPHY(POINT, 4326),
    severity VARCHAR(20) DEFAULT ''info'',
    data JSONB NOT NULL DEFAULT ''{}'',
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS natureos.signal_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type VARCHAR(50) NOT NULL,
    source_device_id UUID REFERENCES natureos.devices(device_id),
    input_data JSONB,
    output_data JSONB,
    status VARCHAR(20) DEFAULT ''pending'',
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS natureos.mesh_networks (
    network_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    network_name VARCHAR(100) NOT NULL,
    network_type VARCHAR(50) DEFAULT ''lora'',
    gateway_device_id UUID REFERENCES natureos.devices(device_id),
    config JSONB DEFAULT ''{}'',
    status VARCHAR(20) DEFAULT ''active'',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_devices_type ON natureos.devices(device_type);
CREATE INDEX IF NOT EXISTS idx_devices_status ON natureos.devices(status);
CREATE INDEX IF NOT EXISTS idx_commands_device ON natureos.commands(device_id);
CREATE INDEX IF NOT EXISTS idx_commands_status ON natureos.commands(status);
CREATE INDEX IF NOT EXISTS idx_telemetry_device ON natureos.telemetry(device_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON natureos.telemetry(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_type ON natureos.environmental_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_detected ON natureos.environmental_events(detected_at DESC);
