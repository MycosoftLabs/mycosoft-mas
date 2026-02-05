-- Migration 013: Unified Memory System
-- Created: February 5, 2026

CREATE SCHEMA IF NOT EXISTS memory;

CREATE TABLE IF NOT EXISTS memory.entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    layer VARCHAR(50) NOT NULL,
    content JSONB NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    accessed_at TIMESTAMPTZ DEFAULT NOW(),
    access_count INTEGER DEFAULT 0,
    importance FLOAT DEFAULT 0.5,
    status VARCHAR(50) DEFAULT 'active',
    tags TEXT[] DEFAULT '{}',
    hash VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_memory_layer ON memory.entries(layer);
CREATE INDEX IF NOT EXISTS idx_memory_importance ON memory.entries(importance DESC);

CREATE SCHEMA IF NOT EXISTS mem0;
CREATE TABLE IF NOT EXISTS mem0.memories (
    id VARCHAR(64) PRIMARY KEY,
    memory TEXT NOT NULL,
    user_id VARCHAR(255),
    agent_id VARCHAR(255),
    hash VARCHAR(64),
    metadata JSONB DEFAULT '{}'::jsonb,
    categories TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE SCHEMA IF NOT EXISTS mcp;
CREATE TABLE IF NOT EXISTS mcp.memories (
    id VARCHAR(64) PRIMARY KEY,
    content TEXT NOT NULL,
    category VARCHAR(50) DEFAULT 'general',
    importance FLOAT DEFAULT 0.5,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE SCHEMA IF NOT EXISTS cross_session;
CREATE TABLE IF NOT EXISTS cross_session.user_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    context_key VARCHAR(255) NOT NULL,
    context_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, context_key)
);
