-- MINDEX Knowledge Graph Schema
-- Migration 023 - February 6, 2026

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create mindex schema if not exists
CREATE SCHEMA IF NOT EXISTS mindex;

-- ============================================
-- KNOWLEDGE NODES
-- ============================================
CREATE TABLE IF NOT EXISTS mindex.knowledge_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_type VARCHAR(50) NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    properties JSONB DEFAULT '{}',
    embedding vector(1536),
    source VARCHAR(100),
    confidence FLOAT DEFAULT 1.0,
    importance FLOAT DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE
);

-- Indexes for knowledge nodes
CREATE INDEX IF NOT EXISTS idx_nodes_type ON mindex.knowledge_nodes(node_type) WHERE NOT is_deleted;
CREATE INDEX IF NOT EXISTS idx_nodes_name ON mindex.knowledge_nodes(name) WHERE NOT is_deleted;
CREATE INDEX IF NOT EXISTS idx_nodes_source ON mindex.knowledge_nodes(source) WHERE NOT is_deleted;
CREATE INDEX IF NOT EXISTS idx_nodes_properties ON mindex.knowledge_nodes USING gin(properties);
CREATE INDEX IF NOT EXISTS idx_nodes_created ON mindex.knowledge_nodes(created_at DESC);

-- Vector similarity index
CREATE INDEX IF NOT EXISTS idx_nodes_embedding 
ON mindex.knowledge_nodes 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- ============================================
-- KNOWLEDGE EDGES
-- ============================================
CREATE TABLE IF NOT EXISTS mindex.knowledge_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES mindex.knowledge_nodes(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES mindex.knowledge_nodes(id) ON DELETE CASCADE,
    edge_type VARCHAR(50) NOT NULL,
    properties JSONB DEFAULT '{}',
    weight FLOAT DEFAULT 1.0,
    is_bidirectional BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_id, target_id, edge_type)
);

-- Indexes for edges
CREATE INDEX IF NOT EXISTS idx_edges_source ON mindex.knowledge_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON mindex.knowledge_edges(target_id);
CREATE INDEX IF NOT EXISTS idx_edges_type ON mindex.knowledge_edges(edge_type);

-- ============================================
-- USER CONTEXTS
-- ============================================
CREATE TABLE IF NOT EXISTS mindex.user_contexts (
    user_id VARCHAR(100) PRIMARY KEY,
    display_name TEXT,
    language VARCHAR(10) DEFAULT 'en',
    timezone VARCHAR(50) DEFAULT 'UTC',
    preferences JSONB DEFAULT '{}',
    recent_activity JSONB DEFAULT '{}',
    saved_views JSONB DEFAULT '[]',
    conversation_summaries JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- SESSION MEMORY
-- ============================================
CREATE TABLE IF NOT EXISTS mindex.session_memory (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) REFERENCES mindex.user_contexts(user_id) ON DELETE SET NULL,
    current_focus JSONB DEFAULT '{}',
    conversation_history JSONB DEFAULT '[]',
    pending_actions JSONB DEFAULT '[]',
    working_memory JSONB DEFAULT '[]',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_interaction_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON mindex.session_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON mindex.session_memory(is_active) WHERE is_active = TRUE;

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION mindex.update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers
DROP TRIGGER IF EXISTS update_nodes_timestamp ON mindex.knowledge_nodes;
CREATE TRIGGER update_nodes_timestamp
    BEFORE UPDATE ON mindex.knowledge_nodes
    FOR EACH ROW EXECUTE FUNCTION mindex.update_timestamp();

DROP TRIGGER IF EXISTS update_edges_timestamp ON mindex.knowledge_edges;
CREATE TRIGGER update_edges_timestamp
    BEFORE UPDATE ON mindex.knowledge_edges
    FOR EACH ROW EXECUTE FUNCTION mindex.update_timestamp();

DROP TRIGGER IF EXISTS update_contexts_timestamp ON mindex.user_contexts;
CREATE TRIGGER update_contexts_timestamp
    BEFORE UPDATE ON mindex.user_contexts
    FOR EACH ROW EXECUTE FUNCTION mindex.update_timestamp();

DROP TRIGGER IF EXISTS update_sessions_timestamp ON mindex.session_memory;
CREATE TRIGGER update_sessions_timestamp
    BEFORE UPDATE ON mindex.session_memory
    FOR EACH ROW EXECUTE FUNCTION mindex.update_timestamp();

-- Graph traversal function
CREATE OR REPLACE FUNCTION mindex.get_neighbors(
    p_node_id UUID,
    p_edge_type VARCHAR DEFAULT NULL,
    p_max_depth INT DEFAULT 1
)
RETURNS TABLE(
    node_id UUID,
    node_type VARCHAR,
    node_name TEXT,
    edge_type VARCHAR,
    depth INT
) AS $$
BEGIN
    RETURN QUERY
    WITH RECURSIVE neighbors AS (
        -- Base case
        SELECT 
            n.id as node_id,
            n.node_type::VARCHAR,
            n.name as node_name,
            e.edge_type::VARCHAR,
            1 as depth
        FROM mindex.knowledge_edges e
        JOIN mindex.knowledge_nodes n ON (
            (e.target_id = n.id AND e.source_id = p_node_id)
            OR (e.source_id = n.id AND e.target_id = p_node_id AND e.is_bidirectional)
        )
        WHERE (p_edge_type IS NULL OR e.edge_type = p_edge_type)
        AND NOT n.is_deleted
        
        UNION
        
        -- Recursive case
        SELECT 
            n.id,
            n.node_type::VARCHAR,
            n.name,
            e.edge_type::VARCHAR,
            nb.depth + 1
        FROM neighbors nb
        JOIN mindex.knowledge_edges e ON (
            e.source_id = nb.node_id
            OR (e.target_id = nb.node_id AND e.is_bidirectional)
        )
        JOIN mindex.knowledge_nodes n ON (
            (e.target_id = n.id AND e.source_id = nb.node_id)
            OR (e.source_id = n.id AND e.target_id = nb.node_id AND e.is_bidirectional)
        )
        WHERE nb.depth < p_max_depth
        AND (p_edge_type IS NULL OR e.edge_type = p_edge_type)
        AND NOT n.is_deleted
    )
    SELECT DISTINCT * FROM neighbors;
END;
$$ LANGUAGE plpgsql;

-- Semantic search function
CREATE OR REPLACE FUNCTION mindex.semantic_search(
    p_embedding vector(1536),
    p_node_type VARCHAR DEFAULT NULL,
    p_limit INT DEFAULT 10,
    p_min_similarity FLOAT DEFAULT 0.5
)
RETURNS TABLE(
    node_id UUID,
    node_type VARCHAR,
    name TEXT,
    description TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        n.id as node_id,
        n.node_type::VARCHAR,
        n.name,
        n.description,
        (1 - (n.embedding <=> p_embedding))::FLOAT as similarity
    FROM mindex.knowledge_nodes n
    WHERE NOT n.is_deleted
    AND n.embedding IS NOT NULL
    AND (p_node_type IS NULL OR n.node_type = p_node_type)
    AND (1 - (n.embedding <=> p_embedding)) >= p_min_similarity
    ORDER BY n.embedding <=> p_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;