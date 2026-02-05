-- Migration 014: Voice Sessions
-- Created: February 5, 2026

CREATE SCHEMA IF NOT EXISTS voice;

CREATE TABLE IF NOT EXISTS voice.sessions (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(255),
    speaker_profile VARCHAR(255),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    turns JSONB DEFAULT '[]'::jsonb,
    context JSONB DEFAULT '{}'::jsonb,
    summary TEXT,
    topics TEXT[] DEFAULT '{}',
    emotional_arc JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_voice_user ON voice.sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_voice_started ON voice.sessions(started_at DESC);
