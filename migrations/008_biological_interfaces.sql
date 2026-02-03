-- Migration 008: Biological Interfaces Schema
-- Created: February 3, 2026

CREATE SCHEMA IF NOT EXISTS bio;

CREATE TABLE IF NOT EXISTS bio.fci_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID,
    species VARCHAR(100),
    strain VARCHAR(100),
    start_time TIMESTAMPTZ DEFAULT NOW(),
    end_time TIMESTAMPTZ,
    config JSONB DEFAULT ''{}'',
    status VARCHAR(20) DEFAULT ''active''
);

CREATE TABLE IF NOT EXISTS bio.electrical_signals (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID REFERENCES bio.fci_sessions(session_id),
    channel INTEGER,
    voltage_mv FLOAT,
    spike_detected BOOLEAN DEFAULT FALSE,
    pattern_class VARCHAR(50),
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bio.stimulation_events (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID,
    stimulation_type VARCHAR(50),
    parameters JSONB,
    electrodes INTEGER[],
    response_recorded BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_signals_session ON bio.electrical_signals(session_id);
CREATE INDEX idx_signals_ts ON bio.electrical_signals(timestamp DESC);
