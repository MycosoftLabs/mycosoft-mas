-- LangGraph Checkpoint Tables Migration
-- Created: February 5, 2026

-- Ensure memory schema exists
CREATE SCHEMA IF NOT EXISTS memory;

-- Checkpoint storage for LangGraph workflows
CREATE TABLE IF NOT EXISTS memory.langgraph_checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    checkpoint_data JSONB NOT NULL,
    metadata JSONB,
    parent_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_id)
);

-- Pending writes storage
CREATE TABLE IF NOT EXISTS memory.langgraph_writes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    value JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_langgraph_checkpoints_thread 
    ON memory.langgraph_checkpoints(thread_id);
CREATE INDEX IF NOT EXISTS idx_langgraph_checkpoints_created 
    ON memory.langgraph_checkpoints(thread_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_langgraph_writes_thread 
    ON memory.langgraph_writes(thread_id, checkpoint_id);

-- Add trigger for updated_at
CREATE OR REPLACE FUNCTION memory.update_langgraph_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS langgraph_checkpoints_updated ON memory.langgraph_checkpoints;
CREATE TRIGGER langgraph_checkpoints_updated
    BEFORE UPDATE ON memory.langgraph_checkpoints
    FOR EACH ROW
    EXECUTE FUNCTION memory.update_langgraph_timestamp();

-- Cleanup old checkpoints (keep last 100 per thread)
CREATE OR REPLACE FUNCTION memory.cleanup_old_checkpoints()
RETURNS void AS $$
BEGIN
    DELETE FROM memory.langgraph_checkpoints
    WHERE (thread_id, checkpoint_id) NOT IN (
        SELECT thread_id, checkpoint_id
        FROM (
            SELECT thread_id, checkpoint_id,
                   ROW_NUMBER() OVER (PARTITION BY thread_id ORDER BY created_at DESC) as rn
            FROM memory.langgraph_checkpoints
        ) ranked
        WHERE rn <= 100
    );
END;
$$ LANGUAGE plpgsql;
