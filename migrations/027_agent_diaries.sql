-- Migration 027: Agent Diaries
-- Created: April 7, 2026
-- Adds AAAK-compressed diary entries for agent session persistence

CREATE TABLE IF NOT EXISTS mindex.agent_diaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    entry_aaak TEXT NOT NULL,
    entry_raw JSONB,
    wing TEXT,
    room TEXT,
    session_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_diary_agent
    ON mindex.agent_diaries(agent_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_diary_session
    ON mindex.agent_diaries(session_id) WHERE session_id IS NOT NULL;
