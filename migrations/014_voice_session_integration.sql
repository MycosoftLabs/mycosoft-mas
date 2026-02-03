-- Voice Session Integration with Memory System - February 3, 2026

CREATE TABLE IF NOT EXISTS memory.voice_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) UNIQUE NOT NULL,
    conversation_id VARCHAR(64) NOT NULL,
    mode VARCHAR(20) NOT NULL CHECK (mode IN ('personaplex', 'elevenlabs', 'whisper')),
    persona VARCHAR(50) DEFAULT 'myca',
    voice_prompt VARCHAR(100),
    user_id UUID REFERENCES memory.user_profiles(user_id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    turn_count INTEGER DEFAULT 0,
    tool_count INTEGER DEFAULT 0,
    avg_latency_ms FLOAT,
    avg_rtf FLOAT,
    total_audio_duration_ms INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_voice_sessions_active ON memory.voice_sessions(is_active);
CREATE INDEX IF NOT EXISTS idx_voice_sessions_user ON memory.voice_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_voice_sessions_started ON memory.voice_sessions(started_at DESC);

CREATE TABLE IF NOT EXISTS memory.voice_turns (
    id SERIAL PRIMARY KEY,
    turn_id VARCHAR(64) UNIQUE NOT NULL,
    session_id VARCHAR(64) NOT NULL REFERENCES memory.voice_sessions(session_id) ON DELETE CASCADE,
    speaker VARCHAR(20) NOT NULL CHECK (speaker IN ('user', 'myca', 'system')),
    text TEXT,
    duration_ms INTEGER,
    latency_ms INTEGER,
    confidence FLOAT,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_voice_turns_session ON memory.voice_turns(session_id);
CREATE INDEX IF NOT EXISTS idx_voice_turns_timestamp ON memory.voice_turns(timestamp DESC);

CREATE TABLE IF NOT EXISTS memory.voice_tool_invocations (
    id SERIAL PRIMARY KEY,
    invocation_id VARCHAR(64) UNIQUE NOT NULL,
    session_id VARCHAR(64) NOT NULL REFERENCES memory.voice_sessions(session_id) ON DELETE CASCADE,
    turn_id VARCHAR(64) REFERENCES memory.voice_turns(turn_id) ON DELETE SET NULL,
    agent VARCHAR(100) NOT NULL,
    action VARCHAR(200),
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'running', 'success', 'error', 'cancelled')),
    latency_ms INTEGER,
    input_params JSONB DEFAULT '{}',
    result JSONB,
    error_message TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_voice_tool_session ON memory.voice_tool_invocations(session_id);
CREATE INDEX IF NOT EXISTS idx_voice_tool_status ON memory.voice_tool_invocations(status);

CREATE TABLE IF NOT EXISTS memory.voice_barge_in_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(64) UNIQUE NOT NULL,
    session_id VARCHAR(64) NOT NULL REFERENCES memory.voice_sessions(session_id) ON DELETE CASCADE,
    cancelled_text TEXT,
    cancelled_at_position_ms INTEGER,
    user_intent VARCHAR(100),
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS memory.persona_voice_prompts (
    id SERIAL PRIMARY KEY,
    prompt_id VARCHAR(64) UNIQUE NOT NULL,
    persona VARCHAR(50) NOT NULL,
    voice_name VARCHAR(100) NOT NULL,
    audio_hash VARCHAR(64),
    audio_path VARCHAR(255),
    sample_rate INTEGER DEFAULT 24000,
    duration_ms INTEGER,
    characteristics JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    use_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE OR REPLACE VIEW memory.voice_session_stats AS SELECT COUNT(*) FILTER (WHERE is_active) as active_sessions, COUNT(*) as total_sessions, SUM(turn_count) as total_turns, SUM(tool_count) as total_tool_invocations FROM memory.voice_sessions;

CREATE OR REPLACE FUNCTION memory.end_voice_session(p_session_id VARCHAR, p_summary TEXT DEFAULT NULL) RETURNS BOOLEAN AS $$ DECLARE v_turn_count INTEGER; v_avg_latency FLOAT; BEGIN SELECT COUNT(*), AVG(latency_ms) INTO v_turn_count, v_avg_latency FROM memory.voice_turns WHERE session_id = p_session_id; UPDATE memory.voice_sessions SET is_active = FALSE, ended_at = NOW(), turn_count = v_turn_count, avg_latency_ms = v_avg_latency, metadata = metadata || jsonb_build_object('summary', p_summary) WHERE session_id = p_session_id; RETURN FOUND; END; $$ LANGUAGE plpgsql;

INSERT INTO memory.persona_voice_prompts (prompt_id, persona, voice_name, duration_ms, is_active) VALUES ('default-myca-voice', 'myca', 'alba-mackenna/casual.wav', 0, TRUE) ON CONFLICT (prompt_id) DO NOTHING;

COMMENT ON TABLE memory.voice_sessions IS 'Voice conversation sessions with PersonaPlex/ElevenLabs';
