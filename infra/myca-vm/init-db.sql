-- MYCA Workspace PostgreSQL initialization
-- Creates databases and schemas needed by MYCA services

-- n8n needs its own schema within the workspace DB
CREATE SCHEMA IF NOT EXISTS n8n;

-- MYCA workspace tables
CREATE TABLE IF NOT EXISTS workspace_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(50) NOT NULL,  -- slack, discord, signal, notion, email
    channel_id VARCHAR(255),
    user_id VARCHAR(255),
    user_name VARCHAR(255),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity TIMESTAMPTZ DEFAULT NOW(),
    context JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS staff_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES workspace_sessions(id),
    staff_member VARCHAR(100) NOT NULL,  -- morgan, rj, garret
    platform VARCHAR(50) NOT NULL,
    direction VARCHAR(10) NOT NULL,  -- inbound, outbound
    message_type VARCHAR(50) DEFAULT 'text',  -- text, file, reaction, scheduled
    content TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    assigned_by VARCHAR(100),
    due_at TIMESTAMPTZ,
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'pending',
    platform VARCHAR(50),  -- where the task came from
    external_id VARCHAR(255),  -- asana task ID, notion page ID, etc.
    result JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS credential_audit_log (
    id BIGSERIAL PRIMARY KEY,
    credential_name VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,  -- accessed, rotated, created
    accessed_by VARCHAR(100) DEFAULT 'myca',
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_interactions_staff ON staff_interactions(staff_member, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_interactions_platform ON staff_interactions(platform, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON workspace_sessions(status, last_activity DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON scheduled_tasks(status, due_at);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON scheduled_tasks(assigned_by, status);
