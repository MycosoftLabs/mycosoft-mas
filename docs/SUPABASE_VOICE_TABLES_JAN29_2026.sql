-- Voice Session Tables for MINDEX/Supabase - January 29, 2026
-- Run this SQL in Supabase Dashboard > SQL Editor

-- Voice Sessions table
CREATE TABLE IF NOT EXISTS voice_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) UNIQUE NOT NULL,
    conversation_id VARCHAR(64) NOT NULL,
    mode VARCHAR(20) NOT NULL CHECK (mode IN ('personaplex', 'elevenlabs')),
    persona VARCHAR(50) DEFAULT 'myca',
    voice_prompt VARCHAR(100),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    turn_count INTEGER DEFAULT 0,
    tool_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'
);

-- Voice Turns table
CREATE TABLE IF NOT EXISTS voice_turns (
    id SERIAL PRIMARY KEY,
    turn_id VARCHAR(64) UNIQUE NOT NULL,
    session_id VARCHAR(64) NOT NULL REFERENCES voice_sessions(session_id) ON DELETE CASCADE,
    speaker VARCHAR(20) NOT NULL CHECK (speaker IN ('user', 'myca', 'system')),
    text TEXT,
    duration_ms INTEGER,
    latency_ms INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tool Invocations table
CREATE TABLE IF NOT EXISTS voice_tool_invocations (
    id SERIAL PRIMARY KEY,
    invocation_id VARCHAR(64) UNIQUE NOT NULL,
    session_id VARCHAR(64) NOT NULL REFERENCES voice_sessions(session_id) ON DELETE CASCADE,
    agent VARCHAR(100) NOT NULL,
    action VARCHAR(200),
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'running', 'success', 'error')),
    latency_ms INTEGER,
    result JSONB,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Barge-in Events table (when user interrupts MYCA)
CREATE TABLE IF NOT EXISTS voice_barge_in_events (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(64) UNIQUE NOT NULL,
    session_id VARCHAR(64) NOT NULL REFERENCES voice_sessions(session_id) ON DELETE CASCADE,
    cancelled_text TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Persona Voice Prompts (store voice conditioning audio hashes)
CREATE TABLE IF NOT EXISTS persona_voice_prompts (
    id SERIAL PRIMARY KEY,
    prompt_id VARCHAR(64) UNIQUE NOT NULL,
    persona VARCHAR(50) NOT NULL,
    voice_name VARCHAR(100) NOT NULL,
    audio_hash VARCHAR(64),  -- SHA256 of audio, not raw audio
    sample_rate INTEGER DEFAULT 24000,
    duration_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_voice_sessions_active ON voice_sessions(is_active);
CREATE INDEX IF NOT EXISTS idx_voice_sessions_mode ON voice_sessions(mode);
CREATE INDEX IF NOT EXISTS idx_voice_sessions_started ON voice_sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_voice_turns_session ON voice_turns(session_id);
CREATE INDEX IF NOT EXISTS idx_voice_turns_timestamp ON voice_turns(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_voice_tool_invocations_session ON voice_tool_invocations(session_id);
CREATE INDEX IF NOT EXISTS idx_voice_tool_invocations_status ON voice_tool_invocations(status);

-- Enable Row Level Security
ALTER TABLE voice_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE voice_turns ENABLE ROW LEVEL SECURITY;
ALTER TABLE voice_tool_invocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE voice_barge_in_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE persona_voice_prompts ENABLE ROW LEVEL SECURITY;

-- Policies (allow authenticated users to read/write)
CREATE POLICY "Allow all operations on voice_sessions" ON voice_sessions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations on voice_turns" ON voice_turns FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations on voice_tool_invocations" ON voice_tool_invocations FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations on voice_barge_in_events" ON voice_barge_in_events FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations on persona_voice_prompts" ON persona_voice_prompts FOR ALL USING (true) WITH CHECK (true);

-- Insert default MYCA voice prompt
INSERT INTO persona_voice_prompts (prompt_id, persona, voice_name, duration_ms)
VALUES ('default-myca-voice', 'myca', 'alba-mackenna/casual.wav', 0)
ON CONFLICT (prompt_id) DO NOTHING;

-- View for active session stats
CREATE OR REPLACE VIEW voice_session_stats AS
SELECT 
    COUNT(*) FILTER (WHERE is_active) as active_sessions,
    COUNT(*) as total_sessions,
    SUM(turn_count) as total_turns,
    SUM(tool_count) as total_tool_invocations
FROM voice_sessions;

-- Function to get session with turns
CREATE OR REPLACE FUNCTION get_session_with_turns(p_session_id VARCHAR)
RETURNS TABLE (
    session_id VARCHAR,
    mode VARCHAR,
    persona VARCHAR,
    started_at TIMESTAMPTZ,
    turn_count BIGINT,
    turns JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.session_id,
        s.mode,
        s.persona,
        s.started_at,
        COUNT(t.id) as turn_count,
        COALESCE(jsonb_agg(
            jsonb_build_object(
                'speaker', t.speaker,
                'text', t.text,
                'timestamp', t.timestamp
            ) ORDER BY t.timestamp
        ) FILTER (WHERE t.id IS NOT NULL), '[]'::jsonb) as turns
    FROM voice_sessions s
    LEFT JOIN voice_turns t ON s.session_id = t.session_id
    WHERE s.session_id = p_session_id
    GROUP BY s.session_id, s.mode, s.persona, s.started_at;
END;
$$ LANGUAGE plpgsql;
