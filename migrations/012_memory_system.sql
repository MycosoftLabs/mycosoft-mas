-- Migration 012: Memory System Schema
-- Created: February 3, 2026

CREATE SCHEMA IF NOT EXISTS memory;

CREATE TABLE IF NOT EXISTS memory.conversations (
    conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_active TIMESTAMPTZ DEFAULT NOW(),
    summary TEXT,
    embedding vector(1536)
);

CREATE TABLE IF NOT EXISTS memory.facts (
    fact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope VARCHAR(50),
    namespace_id UUID,
    key VARCHAR(255),
    value JSONB,
    source VARCHAR(100),
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS memory.user_profiles (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    preferences JSONB DEFAULT ''{}'',
    expertise_domains TEXT[],
    interaction_history JSONB DEFAULT ''[]'',
    memory_consent BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_facts_scope ON memory.facts(scope, namespace_id);
CREATE INDEX idx_conversations_user ON memory.conversations(user_id);
