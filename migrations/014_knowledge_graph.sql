-- Migration: 014_knowledge_graph.sql
-- Created: February 4, 2026
-- Purpose: Knowledge Graph tables for system relationships and semantic connections

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Schema: graph
-- Purpose: Knowledge graph for system relationships
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS graph;

-- Nodes table - entities in the knowledge graph
CREATE TABLE IF NOT EXISTS graph.nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_type VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    properties JSONB DEFAULT '{}',
    embedding FLOAT8[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(name, node_type)
);

CREATE INDEX IF NOT EXISTS idx_nodes_type ON graph.nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_nodes_name ON graph.nodes(name);

-- Edges table - relationships between nodes
CREATE TABLE IF NOT EXISTS graph.edges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES graph.nodes(id) ON DELETE CASCADE,
    target_id UUID REFERENCES graph.nodes(id) ON DELETE CASCADE,
    edge_type VARCHAR(50) NOT NULL,
    properties JSONB DEFAULT '{}',
    weight FLOAT8 DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_id, target_id, edge_type)
);

CREATE INDEX IF NOT EXISTS idx_edges_source ON graph.edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON graph.edges(target_id);
CREATE INDEX IF NOT EXISTS idx_edges_type ON graph.edges(edge_type);

-- Graph metadata table for tracking graph state
CREATE TABLE IF NOT EXISTS graph.metadata (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- Triggers
-- =============================================================================

CREATE OR REPLACE FUNCTION graph_update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_nodes_timestamp') THEN
        CREATE TRIGGER update_nodes_timestamp
            BEFORE UPDATE ON graph.nodes
            FOR EACH ROW EXECUTE FUNCTION graph_update_timestamp();
    END IF;
END $$;

-- =============================================================================
-- Views
-- =============================================================================

CREATE OR REPLACE VIEW graph.v_node_connections AS
SELECT 
    n.id, n.name, n.node_type,
    COUNT(DISTINCT e1.id) as outgoing_edges,
    COUNT(DISTINCT e2.id) as incoming_edges,
    COUNT(DISTINCT e1.id) + COUNT(DISTINCT e2.id) as total_connections
FROM graph.nodes n
LEFT JOIN graph.edges e1 ON e1.source_id = n.id
LEFT JOIN graph.edges e2 ON e2.target_id = n.id
GROUP BY n.id;

CREATE OR REPLACE VIEW graph.v_edge_summary AS
SELECT 
    edge_type,
    COUNT(*) as edge_count,
    AVG(weight) as avg_weight
FROM graph.edges
GROUP BY edge_type;

-- =============================================================================
-- Functions for graph operations
-- =============================================================================

-- Function to get all paths between two nodes (limited depth)
CREATE OR REPLACE FUNCTION graph.find_paths(
    source_uuid UUID,
    target_uuid UUID,
    max_depth INT DEFAULT 5
)
RETURNS TABLE(path UUID[], edge_types TEXT[], total_weight FLOAT8) AS $$
WITH RECURSIVE paths AS (
    -- Base case: start from source
    SELECT 
        ARRAY[source_uuid] as path,
        ARRAY[]::TEXT[] as edge_types,
        0.0::FLOAT8 as total_weight,
        source_uuid as current_node
    WHERE source_uuid IS NOT NULL
    
    UNION ALL
    
    -- Recursive case: extend paths
    SELECT 
        p.path || e.target_id,
        p.edge_types || e.edge_type,
        p.total_weight + e.weight,
        e.target_id
    FROM paths p
    JOIN graph.edges e ON e.source_id = p.current_node
    WHERE 
        NOT e.target_id = ANY(p.path)  -- Avoid cycles
        AND array_length(p.path, 1) < max_depth
)
SELECT path, edge_types, total_weight
FROM paths
WHERE current_node = target_uuid
ORDER BY total_weight
LIMIT 10;
$$ LANGUAGE SQL;

-- Function to get neighbors at distance N
CREATE OR REPLACE FUNCTION graph.get_neighbors(
    center_uuid UUID,
    distance INT DEFAULT 1
)
RETURNS TABLE(node_id UUID, node_name VARCHAR, node_type VARCHAR, hops INT) AS $$
WITH RECURSIVE neighbors AS (
    SELECT id, name, node_type, 0 as hops
    FROM graph.nodes WHERE id = center_uuid
    
    UNION
    
    SELECT n.id, n.name, n.node_type, nb.hops + 1
    FROM neighbors nb
    JOIN graph.edges e ON e.source_id = nb.id OR e.target_id = nb.id
    JOIN graph.nodes n ON n.id = CASE 
        WHEN e.source_id = nb.id THEN e.target_id 
        ELSE e.source_id 
    END
    WHERE nb.hops < distance AND n.id != center_uuid
)
SELECT DISTINCT node_id, node_name, node_type, MIN(hops) as hops
FROM neighbors
WHERE id != center_uuid
GROUP BY node_id, node_name, node_type
ORDER BY hops;
$$ LANGUAGE SQL;

-- Initialize metadata
INSERT INTO graph.metadata (key, value) VALUES
    ('version', '"1.0"'),
    ('created_at', to_jsonb(NOW())),
    ('description', '"Mycosoft Knowledge Graph"')
ON CONFLICT (key) DO NOTHING;
