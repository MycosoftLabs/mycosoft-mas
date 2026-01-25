-- MAS v2 MINDEX Schema Additions
-- Agent activity logging and snapshot storage

-- Agent activity logs table
CREATE TABLE IF NOT EXISTS agent_logs (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    action_type VARCHAR(100) NOT NULL,
    input_summary TEXT,
    output_summary TEXT,
    success BOOLEAN DEFAULT TRUE,
    duration_ms INTEGER DEFAULT 0,
    resources_used JSONB DEFAULT '{}',
    related_agents TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}'
);

-- Index for fast agent lookups
CREATE INDEX IF NOT EXISTS idx_agent_logs_agent_id ON agent_logs(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_timestamp ON agent_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_agent_logs_action_type ON agent_logs(action_type);
CREATE INDEX IF NOT EXISTS idx_agent_logs_agent_timestamp ON agent_logs(agent_id, timestamp DESC);

-- Agent state snapshots table
CREATE TABLE IF NOT EXISTS agent_snapshots (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    snapshot_time TIMESTAMPTZ DEFAULT NOW(),
    state JSONB NOT NULL,
    config JSONB NOT NULL,
    pending_tasks JSONB DEFAULT '[]',
    memory_state JSONB DEFAULT '{}',
    reason VARCHAR(255) DEFAULT 'manual'
);

-- Index for snapshot lookups
CREATE INDEX IF NOT EXISTS idx_agent_snapshots_agent_id ON agent_snapshots(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_snapshots_time ON agent_snapshots(snapshot_time DESC);

-- Agent metrics table for performance tracking
CREATE TABLE IF NOT EXISTS agent_metrics (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    cpu_percent FLOAT DEFAULT 0,
    memory_mb INTEGER DEFAULT 0,
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    avg_task_duration_ms FLOAT DEFAULT 0,
    messages_sent INTEGER DEFAULT 0,
    messages_received INTEGER DEFAULT 0,
    uptime_seconds INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0
);

-- Index for metrics
CREATE INDEX IF NOT EXISTS idx_agent_metrics_agent_id ON agent_metrics(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_timestamp ON agent_metrics(timestamp DESC);

-- Agent communication logs
CREATE TABLE IF NOT EXISTS agent_messages (
    id SERIAL PRIMARY KEY,
    message_id UUID NOT NULL,
    from_agent VARCHAR(100) NOT NULL,
    to_agent VARCHAR(100) NOT NULL,
    message_type VARCHAR(50) NOT NULL,
    payload JSONB DEFAULT '{}',
    priority INTEGER DEFAULT 5,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    correlation_id UUID,
    acknowledged BOOLEAN DEFAULT FALSE,
    ack_time TIMESTAMPTZ
);

-- Index for message lookups
CREATE INDEX IF NOT EXISTS idx_agent_messages_from ON agent_messages(from_agent);
CREATE INDEX IF NOT EXISTS idx_agent_messages_to ON agent_messages(to_agent);
CREATE INDEX IF NOT EXISTS idx_agent_messages_timestamp ON agent_messages(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_agent_messages_correlation ON agent_messages(correlation_id);

-- Agent knowledge store
CREATE TABLE IF NOT EXISTS agent_knowledge (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    UNIQUE(agent_id, key)
);

-- Index for knowledge lookups
CREATE INDEX IF NOT EXISTS idx_agent_knowledge_agent_id ON agent_knowledge(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_knowledge_key ON agent_knowledge(key);

-- Function to clean up old logs (run periodically)
CREATE OR REPLACE FUNCTION cleanup_old_agent_logs(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM agent_logs 
    WHERE timestamp < NOW() - (days_to_keep || ' days')::INTERVAL;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up old metrics (run periodically)
CREATE OR REPLACE FUNCTION cleanup_old_agent_metrics(days_to_keep INTEGER DEFAULT 7)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM agent_metrics 
    WHERE timestamp < NOW() - (days_to_keep || ' days')::INTERVAL;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- View for agent activity summary
CREATE OR REPLACE VIEW agent_activity_summary AS
SELECT 
    agent_id,
    COUNT(*) as total_actions,
    COUNT(*) FILTER (WHERE success = TRUE) as successful_actions,
    COUNT(*) FILTER (WHERE success = FALSE) as failed_actions,
    AVG(duration_ms) as avg_duration_ms,
    MAX(timestamp) as last_activity,
    MIN(timestamp) as first_activity
FROM agent_logs
GROUP BY agent_id;

-- View for recent agent errors
CREATE OR REPLACE VIEW recent_agent_errors AS
SELECT 
    agent_id,
    action_type,
    input_summary,
    output_summary,
    timestamp
FROM agent_logs
WHERE success = FALSE
ORDER BY timestamp DESC
LIMIT 100;

-- Grant permissions (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON agent_logs TO mas_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON agent_snapshots TO mas_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON agent_metrics TO mas_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON agent_messages TO mas_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON agent_knowledge TO mas_user;
