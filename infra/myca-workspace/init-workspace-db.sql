-- MYCA Workspace Database Schema

CREATE TABLE IF NOT EXISTS myca_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(100) DEFAULT 'morgan',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_active TIMESTAMPTZ DEFAULT NOW(),
    context JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS myca_interactions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) REFERENCES myca_sessions(session_id),
    direction VARCHAR(10) NOT NULL, -- 'user' or 'myca'
    content TEXT NOT NULL,
    channel VARCHAR(50) DEFAULT 'chat', -- chat, email, discord, asana
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS myca_actions (
    id SERIAL PRIMARY KEY,
    action_type VARCHAR(100) NOT NULL, -- email, discord, asana, code
    payload JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    result JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS myca_tasks (
    id SERIAL PRIMARY KEY,
    asana_id VARCHAR(100),
    title TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    due_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_sessions_user ON myca_sessions(user_id);
CREATE INDEX idx_interactions_session ON myca_interactions(session_id);
CREATE INDEX idx_interactions_ts ON myca_interactions(timestamp DESC);
CREATE INDEX idx_actions_type ON myca_actions(action_type);
CREATE INDEX idx_actions_status ON myca_actions(status);
