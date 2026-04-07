-- Migration 026: Temporal Knowledge Graph
-- Created: April 7, 2026
-- Adds temporal validity windows to knowledge edges for contradiction detection

-- Add temporal columns to knowledge_edges
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'mindex' AND table_name = 'knowledge_edges'
        AND column_name = 'valid_from'
    ) THEN
        ALTER TABLE mindex.knowledge_edges
            ADD COLUMN valid_from TIMESTAMPTZ DEFAULT now(),
            ADD COLUMN valid_to TIMESTAMPTZ,
            ADD COLUMN confidence FLOAT DEFAULT 1.0,
            ADD COLUMN source_closet TEXT,
            ADD COLUMN source_file TEXT;
    END IF;
END $$;

-- Also add to graph.edges if that schema exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'graph' AND table_name = 'edges'
    ) THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'graph' AND table_name = 'edges'
            AND column_name = 'valid_from'
        ) THEN
            ALTER TABLE graph.edges
                ADD COLUMN valid_from TIMESTAMPTZ DEFAULT now(),
                ADD COLUMN valid_to TIMESTAMPTZ,
                ADD COLUMN confidence FLOAT DEFAULT 1.0,
                ADD COLUMN source_closet TEXT,
                ADD COLUMN source_file TEXT;
        END IF;
    END IF;
END $$;

-- Index for temporal queries
CREATE INDEX IF NOT EXISTS idx_edge_temporal
    ON mindex.knowledge_edges(valid_from, valid_to);

-- Index for currently valid edges
CREATE INDEX IF NOT EXISTS idx_edge_currently_valid
    ON mindex.knowledge_edges(source_id, edge_type)
    WHERE valid_to IS NULL;
