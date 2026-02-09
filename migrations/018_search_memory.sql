-- Migration 018: Search Memory Integration
-- Created: February 5, 2026
-- Purpose: Add tables for search session memory and user interest tracking

-- Ensure mindex schema exists
CREATE SCHEMA IF NOT EXISTS mindex;

-- ============================================================================
-- Search Sessions - Stores completed search sessions
-- ============================================================================

CREATE TABLE IF NOT EXISTS mindex.search_sessions (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    query_count INTEGER DEFAULT 0,
    species_explored INTEGER DEFAULT 0,
    ai_interactions INTEGER DEFAULT 0,
    session_data JSONB,  -- Full session serialization
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_search_sessions_user ON mindex.search_sessions(user_id);
CREATE INDEX idx_search_sessions_started ON mindex.search_sessions(started_at DESC);
CREATE INDEX idx_search_sessions_user_recent ON mindex.search_sessions(user_id, started_at DESC);

-- ============================================================================
-- User Interests - Tracks user interest in taxa
-- ============================================================================

CREATE TABLE IF NOT EXISTS mindex.user_interests (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    taxon_id INTEGER NOT NULL,  -- References mindex.taxa
    interest_type VARCHAR(50) NOT NULL,  -- 'search', 'focus', 'ai_question', 'bookmark'
    interest_score FLOAT DEFAULT 0.5,  -- 0.0 to 1.0
    interaction_count INTEGER DEFAULT 1,
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB,
    CONSTRAINT uk_user_interest UNIQUE (user_id, taxon_id, interest_type)
);

CREATE INDEX idx_user_interests_user ON mindex.user_interests(user_id);
CREATE INDEX idx_user_interests_taxon ON mindex.user_interests(taxon_id);
CREATE INDEX idx_user_interests_score ON mindex.user_interests(user_id, interest_score DESC);
CREATE INDEX idx_user_interests_recent ON mindex.user_interests(last_seen_at DESC);

-- ============================================================================
-- Search Analytics - Query-level analytics
-- ============================================================================

CREATE TABLE IF NOT EXISTS mindex.search_analytics (
    id BIGSERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    query_normalized TEXT,  -- Lowercase, trimmed
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    result_count INTEGER DEFAULT 0,
    clicked_results JSONB,  -- List of clicked result IDs
    response_time_ms INTEGER,
    source VARCHAR(50) DEFAULT ''text'',  -- 'text', 'voice', 'suggestion'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_search_analytics_query ON mindex.search_analytics(query_normalized);
CREATE INDEX idx_search_analytics_user ON mindex.search_analytics(user_id);
CREATE INDEX idx_search_analytics_time ON mindex.search_analytics(created_at DESC);

-- Function to normalize queries
CREATE OR REPLACE FUNCTION mindex.normalize_query()
RETURNS TRIGGER AS $$
BEGIN
    NEW.query_normalized := LOWER(TRIM(NEW.query));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for query normalization
DROP TRIGGER IF EXISTS trg_normalize_query ON mindex.search_analytics;
CREATE TRIGGER trg_normalize_query
    BEFORE INSERT OR UPDATE ON mindex.search_analytics
    FOR EACH ROW EXECUTE FUNCTION mindex.normalize_query();

-- ============================================================================
-- Popular Searches View - For autocomplete and suggestions
-- ============================================================================

CREATE OR REPLACE VIEW mindex.popular_searches AS
SELECT 
    query_normalized as query,
    COUNT(*) as search_count,
    COUNT(DISTINCT user_id) as unique_users,
    AVG(result_count) as avg_results,
    MAX(created_at) as last_searched
FROM mindex.search_analytics
WHERE created_at > NOW() - INTERVAL ''30 days''
  AND result_count > 0
GROUP BY query_normalized
ORDER BY search_count DESC;

-- ============================================================================
-- User Interest Summary View
-- ============================================================================

CREATE OR REPLACE VIEW mindex.user_interest_summary AS
SELECT 
    ui.user_id,
    t.scientific_name,
    t.common_name,
    ui.interest_score,
    ui.interaction_count,
    ui.interest_type,
    ui.last_seen_at
FROM mindex.user_interests ui
LEFT JOIN mindex.taxa t ON t.taxon_id = ui.taxon_id
ORDER BY ui.interest_score DESC;

-- ============================================================================
-- Session Statistics View
-- ============================================================================

CREATE OR REPLACE VIEW mindex.session_stats AS
SELECT 
    DATE(started_at) as session_date,
    COUNT(*) as session_count,
    COUNT(DISTINCT user_id) as unique_users,
    AVG(query_count) as avg_queries,
    AVG(species_explored) as avg_species,
    AVG(ai_interactions) as avg_ai_messages,
    AVG(EXTRACT(EPOCH FROM (ended_at - started_at))) as avg_duration_seconds
FROM mindex.search_sessions
WHERE ended_at IS NOT NULL
GROUP BY DATE(started_at)
ORDER BY session_date DESC;

-- ============================================================================
-- Update timestamp trigger for search_sessions
-- ============================================================================

CREATE OR REPLACE FUNCTION mindex.update_search_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := NOW();
    
    -- Update summary fields from session_data
    IF NEW.session_data IS NOT NULL THEN
        NEW.query_count := COALESCE(
            jsonb_array_length(NEW.session_data->''queries''), 0
        );
        NEW.species_explored := COALESCE(
            jsonb_array_length(NEW.session_data->''focused_species''), 0
        );
        NEW.ai_interactions := COALESCE(
            jsonb_array_length(NEW.session_data->''ai_conversation''), 0
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_search_session ON mindex.search_sessions;
CREATE TRIGGER trg_update_search_session
    BEFORE INSERT OR UPDATE ON mindex.search_sessions
    FOR EACH ROW EXECUTE FUNCTION mindex.update_search_session_timestamp();

-- ============================================================================
-- RLS Policies (for Supabase)
-- ============================================================================

-- Enable RLS
ALTER TABLE mindex.search_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE mindex.user_interests ENABLE ROW LEVEL SECURITY;
ALTER TABLE mindex.search_analytics ENABLE ROW LEVEL SECURITY;

-- Search sessions - users can only see their own
CREATE POLICY search_sessions_user_policy ON mindex.search_sessions
    FOR ALL
    USING (auth.uid()::text = user_id OR user_id LIKE ''anonymous_%'');

-- User interests - users can only see their own
CREATE POLICY user_interests_user_policy ON mindex.user_interests
    FOR ALL
    USING (auth.uid()::text = user_id);

-- Search analytics - insert only, read for aggregates
CREATE POLICY search_analytics_insert_policy ON mindex.search_analytics
    FOR INSERT
    WITH CHECK (true);

CREATE POLICY search_analytics_select_policy ON mindex.search_analytics
    FOR SELECT
    USING (auth.uid()::text = user_id OR user_id IS NULL);

-- Comments
COMMENT ON TABLE mindex.search_sessions IS ''Completed search sessions with full context'';
COMMENT ON TABLE mindex.user_interests IS ''User interest scores for taxa based on search behavior'';
COMMENT ON TABLE mindex.search_analytics IS ''Individual search query analytics'';
COMMENT ON VIEW mindex.popular_searches IS ''Popular searches in the last 30 days'';
COMMENT ON VIEW mindex.user_interest_summary IS ''User interests with taxa names'';
COMMENT ON VIEW mindex.session_stats IS ''Daily session statistics'';