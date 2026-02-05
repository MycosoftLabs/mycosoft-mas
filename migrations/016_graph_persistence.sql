-- Migration 016: Graph Persistence
-- Created: February 5, 2026

CREATE SCHEMA IF NOT EXISTS graph;

CREATE TABLE IF NOT EXISTS graph.nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_type VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    properties JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(name, node_type)
);

CREATE TABLE IF NOT EXISTS graph.edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES graph.nodes(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES graph.nodes(id) ON DELETE CASCADE,
    edge_type VARCHAR(50) NOT NULL,
    properties JSONB DEFAULT '{}'::jsonb,
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_id, target_id, edge_type)
);

CREATE INDEX IF NOT EXISTS idx_graph_node_type ON graph.nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_graph_edge_source ON graph.edges(source_id);
CREATE INDEX IF NOT EXISTS idx_graph_edge_target ON graph.edges(target_id);
