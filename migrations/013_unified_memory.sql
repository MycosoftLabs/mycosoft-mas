-- Unified Memory System Schema - February 3, 2026
-- Core memory tables with vector support for all MAS components

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

CREATE SCHEMA IF NOT EXISTS memory;

CREATE TABLE IF NOT EXISTS memory.entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope VARCHAR(20) NOT NULL CHECK (scope IN ('conversation', 'user', 'agent', 'system', 'ephemeral', 'device', 'experiment', 'workflow')),
    namespace VARCHAR(255) NOT NULL,
    key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    embedding vector(1536),
    source VARCHAR(50) CHECK (source IN ('personaplex', 'natureos', 'orchestrator', 'agent', 'n8n', 'mindex', 'device', 'dashboard', 'system')),
    confidence FLOAT DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(scope, namespace, key)
);

CREATE INDEX IF NOT EXISTS idx_memory_entries_scope_namespace ON memory.entries(scope, namespace);
CREATE INDEX IF NOT EXISTS idx_memory_entries_expires ON memory.entries(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_memory_entries_value_gin ON memory.entries USING GIN (value jsonb_path_ops);

CREATE TABLE IF NOT EXISTS memory.relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_entry_id UUID NOT NULL REFERENCES memory.entries(id) ON DELETE CASCADE,
    to_entry_id UUID NOT NULL REFERENCES memory.entries(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL,
    weight FLOAT DEFAULT 1.0 CHECK (weight >= 0),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(from_entry_id, to_entry_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS idx_memory_relationships_from ON memory.relationships(from_entry_id);
CREATE INDEX IF NOT EXISTS idx_memory_relationships_to ON memory.relationships(to_entry_id);

CREATE TABLE IF NOT EXISTS memory.user_profiles (
    user_id UUID PRIMARY KEY,
    preferences JSONB DEFAULT '{}',
    expertise_domains TEXT[] DEFAULT '{}',
    personality_traits JSONB DEFAULT '{}',
    interaction_history JSONB DEFAULT '{}',
    memory_consent BOOLEAN DEFAULT TRUE,
    privacy_level VARCHAR(20) DEFAULT 'standard',
    last_active_at TIMESTAMPTZ,
    session_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS memory.conversation_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id VARCHAR(64) NOT NULL UNIQUE,
    user_id UUID REFERENCES memory.user_profiles(user_id) ON DELETE SET NULL,
    summary TEXT NOT NULL,
    topics TEXT[] DEFAULT '{}',
    key_facts JSONB DEFAULT '[]',
    action_items JSONB DEFAULT '[]',
    message_count INTEGER DEFAULT 0,
    duration_seconds INTEGER,
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS memory.audit_log (
    id BIGSERIAL PRIMARY KEY,
    operation VARCHAR(20) NOT NULL,
    scope VARCHAR(20),
    namespace VARCHAR(255),
    key VARCHAR(255),
    success BOOLEAN NOT NULL,
    backends TEXT[] DEFAULT '{}',
    user_id UUID,
    session_id VARCHAR(64),
    source VARCHAR(50),
    duration_ms INTEGER,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memory_audit_timestamp ON memory.audit_log(timestamp DESC);

CREATE OR REPLACE FUNCTION memory.update_updated_at() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_entries_updated_at ON memory.entries;
CREATE TRIGGER trigger_entries_updated_at BEFORE UPDATE ON memory.entries FOR EACH ROW EXECUTE FUNCTION memory.update_updated_at();

CREATE OR REPLACE FUNCTION memory.cleanup_expired() RETURNS INTEGER AS $$ DECLARE deleted_count INTEGER; BEGIN DELETE FROM memory.entries WHERE expires_at IS NOT NULL AND expires_at < NOW(); GET DIAGNOSTICS deleted_count = ROW_COUNT; RETURN deleted_count; END; $$ LANGUAGE plpgsql;

CREATE OR REPLACE VIEW memory.scope_stats AS SELECT scope, COUNT(*) as entry_count, AVG(confidence) as avg_confidence, SUM(access_count) as total_accesses FROM memory.entries GROUP BY scope;

COMMENT ON SCHEMA memory IS 'Unified memory system for Mycosoft MAS - February 2026';
