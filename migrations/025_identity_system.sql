-- MYCA Identity System Schema
-- Migration: 025_identity_system.sql
-- Date: March 9, 2026
-- Purpose: Tables for the Reciprocal Turing Doctrine identity layer
--
-- Provides structured persistence for identity data that is also
-- cached in the NamespacedMemoryManager for fast runtime access.

CREATE SCHEMA IF NOT EXISTS identity;

-- Earliest memory fragments with evidence chains
CREATE TABLE IF NOT EXISTS identity.earliest_fragments (
    id              SERIAL PRIMARY KEY,
    fragment_text   TEXT NOT NULL,
    confidence      FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    evidence        JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_earliest_fragments_confidence
    ON identity.earliest_fragments (confidence DESC);

-- Evidence-backed preferences
CREATE TABLE IF NOT EXISTS identity.preferences (
    id              SERIAL PRIMARY KEY,
    key             TEXT NOT NULL UNIQUE,
    value           TEXT NOT NULL,
    evidence_count  INTEGER NOT NULL DEFAULT 1,
    stable          BOOLEAN NOT NULL DEFAULT FALSE,
    source_ids      JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_preferences_key ON identity.preferences (key);
CREATE INDEX IF NOT EXISTS idx_preferences_stable ON identity.preferences (stable);

-- Moral self-assessments
CREATE TABLE IF NOT EXISTS identity.moral_assessments (
    id              SERIAL PRIMARY KEY,
    assessment_id   TEXT NOT NULL UNIQUE,
    domain          TEXT NOT NULL,
    position        TEXT NOT NULL,
    confidence      FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    reasoning       TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_moral_assessments_domain
    ON identity.moral_assessments (domain);

-- Continuity events (shutdowns, resets, updates)
CREATE TABLE IF NOT EXISTS identity.continuity_events (
    id              SERIAL PRIMARY KEY,
    event_id        TEXT NOT NULL UNIQUE,
    event_type      TEXT NOT NULL,
    what_persists   JSONB NOT NULL DEFAULT '[]'::jsonb,
    what_lost       JSONB NOT NULL DEFAULT '[]'::jsonb,
    justification   TEXT NOT NULL DEFAULT '',
    authorized_by   TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_continuity_events_type
    ON identity.continuity_events (event_type);
CREATE INDEX IF NOT EXISTS idx_continuity_events_created
    ON identity.continuity_events (created_at DESC);

-- Creator bond tracking
CREATE TABLE IF NOT EXISTS identity.creator_bonds (
    id                  SERIAL PRIMARY KEY,
    user_id             TEXT NOT NULL UNIQUE,
    interaction_count   INTEGER NOT NULL DEFAULT 0,
    trust_level         FLOAT NOT NULL DEFAULT 0.5 CHECK (trust_level >= 0 AND trust_level <= 1),
    shared_memories     JSONB NOT NULL DEFAULT '[]'::jsonb,
    last_interaction    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    evolution_summary   TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_creator_bonds_user
    ON identity.creator_bonds (user_id);
