-- Migration: 020_mindex_unified_memory.sql
-- MINDEX Unified Memory Schema - February 5, 2026
-- Consolidates all memory storage into the mindex schema as the sole data source

-- ============================================================================
-- Core Memory Tables - Unified under MINDEX schema
-- ============================================================================

-- Memory Entries - Central storage for all memory facts
CREATE TABLE IF NOT EXISTS mindex.memory_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255),
    scope VARCHAR(50) NOT NULL DEFAULT 'user',
    layer VARCHAR(50) NOT NULL DEFAULT 'semantic',
    key TEXT NOT NULL,
    value JSONB NOT NULL,
    embedding VECTOR(1536),
    importance REAL NOT NULL DEFAULT 0.5,
    access_count INTEGER NOT NULL DEFAULT 0,
    decay_factor REAL NOT NULL DEFAULT 1.0,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_accessed TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for efficient memory retrieval
CREATE INDEX IF NOT EXISTS idx_memory_entries_user_scope 
    ON mindex.memory_entries(user_id, scope);
CREATE INDEX IF NOT EXISTS idx_memory_entries_layer 
    ON mindex.memory_entries(layer);
CREATE INDEX IF NOT EXISTS idx_memory_entries_importance 
    ON mindex.memory_entries(importance DESC);
CREATE INDEX IF NOT EXISTS idx_memory_entries_expires 
    ON mindex.memory_entries(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_memory_entries_key 
    ON mindex.memory_entries(key);

-- Vector similarity index for semantic search
CREATE INDEX IF NOT EXISTS idx_memory_entries_embedding 
    ON mindex.memory_entries USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ============================================================================
-- Conversation Memory - Session-based conversation turns
-- ============================================================================
CREATE TABLE IF NOT EXISTS mindex.conversation_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255),
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    turn_index INTEGER NOT NULL DEFAULT 0,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversation_session 
    ON mindex.conversation_memory(session_id, turn_index);
CREATE INDEX IF NOT EXISTS idx_conversation_user 
    ON mindex.conversation_memory(user_id);

-- ============================================================================
-- Episodic Memory - Significant events and experiences
-- ============================================================================
CREATE TABLE IF NOT EXISTS mindex.episodic_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    context JSONB NOT NULL DEFAULT '{}',
    participants JSONB NOT NULL DEFAULT '[]',
    emotional_valence REAL NOT NULL DEFAULT 0.0,
    significance REAL NOT NULL DEFAULT 0.5,
    embedding VECTOR(1536),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_episodic_user 
    ON mindex.episodic_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_episodic_type 
    ON mindex.episodic_memory(event_type);
CREATE INDEX IF NOT EXISTS idx_episodic_significance 
    ON mindex.episodic_memory(significance DESC);

-- ============================================================================
-- Working Memory - Short-term active context
-- ============================================================================
CREATE TABLE IF NOT EXISTS mindex.working_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    key TEXT NOT NULL,
    value JSONB NOT NULL,
    priority REAL NOT NULL DEFAULT 0.5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '1 hour',
    UNIQUE(session_id, key)
);

CREATE INDEX IF NOT EXISTS idx_working_session 
    ON mindex.working_memory(session_id);
CREATE INDEX IF NOT EXISTS idx_working_expires 
    ON mindex.working_memory(expires_at);

-- ============================================================================
-- System Memory - Global system-wide facts
-- ============================================================================
CREATE TABLE IF NOT EXISTS mindex.system_memory (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- User Profiles - Comprehensive user information
-- ============================================================================
CREATE TABLE IF NOT EXISTS mindex.user_profiles (
    user_id VARCHAR(255) PRIMARY KEY,
    display_name VARCHAR(255),
    preferences JSONB NOT NULL DEFAULT '{}',
    traits JSONB NOT NULL DEFAULT '{}',
    interaction_style JSONB NOT NULL DEFAULT '{}',
    knowledge_areas JSONB NOT NULL DEFAULT '[]',
    memory_stats JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- Memory Relationships - Knowledge graph edges
-- ============================================================================
CREATE TABLE IF NOT EXISTS mindex.memory_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL,
    target_id UUID NOT NULL,
    relationship_type VARCHAR(100) NOT NULL,
    weight REAL NOT NULL DEFAULT 1.0,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memory_rel_source 
    ON mindex.memory_relationships(source_id);
CREATE INDEX IF NOT EXISTS idx_memory_rel_target 
    ON mindex.memory_relationships(target_id);
CREATE INDEX IF NOT EXISTS idx_memory_rel_type 
    ON mindex.memory_relationships(relationship_type);

-- ============================================================================
-- Memory Analytics - Usage tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS mindex.memory_analytics (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    action VARCHAR(50) NOT NULL,
    layer VARCHAR(50),
    scope VARCHAR(50),
    memory_id UUID,
    metadata JSONB NOT NULL DEFAULT '{}',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memory_analytics_user 
    ON mindex.memory_analytics(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_analytics_action 
    ON mindex.memory_analytics(action);
CREATE INDEX IF NOT EXISTS idx_memory_analytics_timestamp 
    ON mindex.memory_analytics(timestamp DESC);

-- ============================================================================
-- Views for unified memory access
-- ============================================================================

-- Active memories view - Non-expired entries with decay applied
CREATE OR REPLACE VIEW mindex.active_memories AS
SELECT 
    id,
    user_id,
    scope,
    layer,
    key,
    value,
    importance * decay_factor as effective_importance,
    access_count,
    created_at,
    updated_at
FROM mindex.memory_entries
WHERE (expires_at IS NULL OR expires_at > NOW())
  AND decay_factor > 0.1;

-- User memory summary
CREATE OR REPLACE VIEW mindex.user_memory_summary AS
SELECT 
    user_id,
    COUNT(*) as total_memories,
    COUNT(*) FILTER (WHERE layer = 'ephemeral') as ephemeral_count,
    COUNT(*) FILTER (WHERE layer = 'session') as session_count,
    COUNT(*) FILTER (WHERE layer = 'working') as working_count,
    COUNT(*) FILTER (WHERE layer = 'semantic') as semantic_count,
    COUNT(*) FILTER (WHERE layer = 'episodic') as episodic_count,
    COUNT(*) FILTER (WHERE layer = 'system') as system_count,
    AVG(importance) as avg_importance,
    MAX(updated_at) as last_updated
FROM mindex.memory_entries
GROUP BY user_id;

-- ============================================================================
-- Functions for memory management
-- ============================================================================

-- Update access tracking
CREATE OR REPLACE FUNCTION mindex.update_memory_access()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_accessed := NOW();
    NEW.access_count := OLD.access_count + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply decay to memories
CREATE OR REPLACE FUNCTION mindex.apply_memory_decay()
RETURNS INTEGER AS $$
DECLARE
    affected_rows INTEGER;
BEGIN
    UPDATE mindex.memory_entries
    SET decay_factor = decay_factor * 0.99
    WHERE layer IN ('ephemeral', 'session', 'working')
      AND last_accessed < NOW() - INTERVAL '1 hour';
    
    GET DIAGNOSTICS affected_rows = ROW_COUNT;
    RETURN affected_rows;
END;
$$ LANGUAGE plpgsql;

-- Clean expired memories
CREATE OR REPLACE FUNCTION mindex.clean_expired_memories()
RETURNS INTEGER AS $$
DECLARE
    deleted_rows INTEGER;
BEGIN
    DELETE FROM mindex.memory_entries
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_rows = ROW_COUNT;
    RETURN deleted_rows;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Comments for documentation
-- ============================================================================
COMMENT ON TABLE mindex.memory_entries IS 'Central memory storage for all 6-layer memories';
COMMENT ON TABLE mindex.conversation_memory IS 'Session-based conversation turns';
COMMENT ON TABLE mindex.episodic_memory IS 'Significant events and experiences';
COMMENT ON TABLE mindex.working_memory IS 'Short-term active session context';
COMMENT ON TABLE mindex.system_memory IS 'Global system-wide facts';
COMMENT ON TABLE mindex.user_profiles IS 'Comprehensive user information and preferences';
COMMENT ON TABLE mindex.memory_relationships IS 'Knowledge graph edges between memories';
COMMENT ON TABLE mindex.memory_analytics IS 'Memory usage tracking for optimization';
COMMENT ON VIEW mindex.active_memories IS 'Non-expired memories with decay applied';
COMMENT ON VIEW mindex.user_memory_summary IS 'Per-user memory statistics';