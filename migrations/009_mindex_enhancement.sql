-- Migration 009: MINDEX Enhancement with Vector Search
-- Created: February 3, 2026

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS mindex.embeddings (
    id BIGSERIAL PRIMARY KEY,
    entity_type VARCHAR(50),
    entity_id UUID,
    embedding vector(1536),
    model_version VARCHAR(50) DEFAULT ''text-embedding-3-small'',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mindex.knowledge_edges (
    id BIGSERIAL PRIMARY KEY,
    source_entity_id UUID,
    target_entity_id UUID,
    relationship_type VARCHAR(100),
    confidence FLOAT DEFAULT 1.0,
    evidence JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_embeddings_entity ON mindex.embeddings(entity_type, entity_id);
CREATE INDEX idx_knowledge_edges_source ON mindex.knowledge_edges(source_entity_id);
CREATE INDEX idx_knowledge_edges_target ON mindex.knowledge_edges(target_entity_id);
