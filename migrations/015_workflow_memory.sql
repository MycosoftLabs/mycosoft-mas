-- Migration 015: Workflow Memory
-- Created: February 5, 2026

CREATE SCHEMA IF NOT EXISTS workflow;

CREATE TABLE IF NOT EXISTS workflow.executions (
    id VARCHAR(64) PRIMARY KEY,
    workflow_id VARCHAR(255) NOT NULL,
    workflow_name VARCHAR(255),
    category VARCHAR(50),
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    duration_ms INTEGER,
    trigger VARCHAR(50) DEFAULT 'manual',
    input_data JSONB DEFAULT '{}'::jsonb,
    output_data JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    error_node VARCHAR(255),
    nodes_executed INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workflow.patterns (
    id VARCHAR(64) PRIMARY KEY,
    workflow_id VARCHAR(255) NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,
    description TEXT,
    frequency INTEGER DEFAULT 0,
    last_seen TIMESTAMPTZ,
    conditions JSONB DEFAULT '{}'::jsonb,
    recommendations TEXT[] DEFAULT '{}',
    confidence FLOAT DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
