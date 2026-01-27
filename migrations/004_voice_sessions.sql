-- Voice Session Tables for MINDEX - January 27, 2026

-- Voice Sessions table
CREATE TABLE IF NOT EXISTS voice_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) UNIQUE NOT NULL,
    conversation_id VARCHAR(64) NOT NULL,
    mode VARCHAR(20) NOT NULL CHECK (mode IN ('personaplex', 'elevenlabs')),
    persona VARCHAR(50) DEFAULT 'myca',
    voice_prompt VARCHAR(50),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'
);

-- Voice Turns table
CREATE TABLE IF NOT EXISTS voice_turns (
    id SERIAL PRIMARY KEY,
    turn_id VARCHAR(64) UNIQUE NOT NULL,
    session_id VARCHAR(64) NOT NULL,
    speaker VARCHAR(20) NOT NULL CHECK (speaker IN ('user', 'myca', 'system')),
    text TEXT,
    duration_ms INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tool Invocations table
CREATE TABLE IF NOT EXISTS voice_tool_invocations (
    id SERIAL PRIMARY KEY,
    invocation_id VARCHAR(64) UNIQUE NOT NULL,
    session_id VARCHAR(64) NOT NULL,
    agent VARCHAR(100) NOT NULL,
    action VARCHAR(200),
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'running', 'success', 'error')),
    latency_ms INTEGER,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Barge-in Events table
CREATE TABLE IF NOT EXISTS voice_barge_in_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(64) UNIQUE NOT NULL,
    session_id VARCHAR(64) NOT NULL,
    cancelled_text TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_voice_sessions_active ON voice_sessions(is_active);
CREATE INDEX IF NOT EXISTS idx_voice_turns_session ON voice_turns(session_id);
CREATE INDEX IF NOT EXISTS idx_voice_tool_invocations_session ON voice_tool_invocations(session_id);
