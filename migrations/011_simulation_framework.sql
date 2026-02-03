-- Migration 011: Simulation Framework Schema
-- Created: February 3, 2026

CREATE SCHEMA IF NOT EXISTS simulation;

CREATE TABLE IF NOT EXISTS simulation.runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_type VARCHAR(50),
    config JSONB,
    status VARCHAR(20) DEFAULT ''pending'',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    result_summary JSONB,
    artifacts_path TEXT
);

CREATE TABLE IF NOT EXISTS simulation.hypotheses (
    hypothesis_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt TEXT,
    formulation TEXT,
    simulation_runs UUID[],
    validation_status VARCHAR(20) DEFAULT ''untested'',
    confidence FLOAT DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sim_runs_type ON simulation.runs(simulation_type);
CREATE INDEX idx_sim_runs_status ON simulation.runs(status);
