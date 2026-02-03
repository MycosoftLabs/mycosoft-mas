-- Migration 007: Device Registry Schema
-- Created: February 3, 2026

CREATE SCHEMA IF NOT EXISTS devices;

CREATE TABLE IF NOT EXISTS devices.registry (
    device_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_class VARCHAR(50) NOT NULL,
    hardware_version VARCHAR(20),
    firmware_version VARCHAR(20),
    capabilities JSONB DEFAULT ''[]'',
    calibration_data JSONB DEFAULT ''{}'',
    location GEOGRAPHY(POINT, 4326),
    mesh_network_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS devices.telemetry (
    id BIGSERIAL PRIMARY KEY,
    device_id UUID REFERENCES devices.registry(device_id),
    sensor_type VARCHAR(50),
    reading JSONB,
    quality_score FLOAT DEFAULT 1.0,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS devices.commands_log (
    id BIGSERIAL PRIMARY KEY,
    device_id UUID,
    command_type VARCHAR(50),
    payload JSONB,
    response JSONB,
    status VARCHAR(20),
    latency_ms INTEGER,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_devices_class ON devices.registry(device_class);
CREATE INDEX idx_telemetry_device_ts ON devices.telemetry(device_id, timestamp DESC);
