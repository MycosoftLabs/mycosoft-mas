-- MYCA OS Database Tables
-- Run on MINDEX PostgreSQL (192.168.0.189:5432, database: mycosoft_mas)
-- Date: 2026-03-04

BEGIN;

-- ════════════════════════════════════════════════════════════
-- 1. MYCA Events — Append-only audit trail for all OS events
-- ════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS myca_events (
    id              BIGSERIAL PRIMARY KEY,
    event_type      VARCHAR(100) NOT NULL,
    event_data      JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_myca_events_type ON myca_events (event_type);
CREATE INDEX IF NOT EXISTS idx_myca_events_created ON myca_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_myca_events_data ON myca_events USING gin (event_data);

-- ════════════════════════════════════════════════════════════
-- 2. Agent Memory — 6-layer memory system storage
-- ════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS agent_memory (
    id              BIGSERIAL PRIMARY KEY,
    agent_id        VARCHAR(100) NOT NULL,
    memory_key      VARCHAR(500) NOT NULL,
    memory_value    TEXT,
    memory_layer    VARCHAR(50) NOT NULL DEFAULT 'working',
    confidence      REAL DEFAULT 1.0,
    access_count    INTEGER DEFAULT 0,
    last_accessed   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(agent_id, memory_key, memory_layer)
);

CREATE INDEX IF NOT EXISTS idx_agent_memory_agent ON agent_memory (agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_memory_layer ON agent_memory (memory_layer);
CREATE INDEX IF NOT EXISTS idx_agent_memory_key ON agent_memory (memory_key);

-- ════════════════════════════════════════════════════════════
-- 3. MYCA Task Queue — Persistent executive task queue
-- ════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS myca_task_queue (
    id              BIGSERIAL PRIMARY KEY,
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    priority        VARCHAR(20) NOT NULL DEFAULT 'medium',
    task_type       VARCHAR(50) NOT NULL DEFAULT 'general',
    source          VARCHAR(50) NOT NULL DEFAULT 'self',
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    assigned_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    due_at          TIMESTAMPTZ,
    result          JSONB,
    error           TEXT,
    morgan_approved BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_myca_tasks_status ON myca_task_queue (status);
CREATE INDEX IF NOT EXISTS idx_myca_tasks_priority ON myca_task_queue (priority);

-- ════════════════════════════════════════════════════════════
-- 4. MYCA Decisions — Decision audit log
-- ════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS myca_decisions (
    id              BIGSERIAL PRIMARY KEY,
    decision_type   VARCHAR(100) NOT NULL,
    decision_level  VARCHAR(20) NOT NULL,
    description     TEXT,
    action_taken    VARCHAR(50),
    rationale       TEXT,
    morgan_response VARCHAR(50),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_myca_decisions_type ON myca_decisions (decision_type);
CREATE INDEX IF NOT EXISTS idx_myca_decisions_level ON myca_decisions (decision_level);

-- ════════════════════════════════════════════════════════════
-- 5. MYCA Schedule — Daily/weekly/recurring schedule
-- ════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS myca_schedule (
    id              BIGSERIAL PRIMARY KEY,
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    schedule_type   VARCHAR(20) NOT NULL DEFAULT 'once',  -- once, daily, weekly, monthly, cron
    cron_expr       VARCHAR(100),                          -- for cron type
    day_of_week     INTEGER,                               -- 0=Mon for weekly
    time_of_day     TIME,                                  -- HH:MM for daily/weekly
    scheduled_at    TIMESTAMPTZ,                           -- for once type
    task_type       VARCHAR(50) DEFAULT 'general',
    task_data       JSONB DEFAULT '{}',
    enabled         BOOLEAN DEFAULT TRUE,
    last_run        TIMESTAMPTZ,
    next_run        TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_myca_schedule_next ON myca_schedule (next_run) WHERE enabled = TRUE;

-- ════════════════════════════════════════════════════════════
-- 6. MYCA Messages — Inbound/outbound message log
-- ════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS myca_messages (
    id              BIGSERIAL PRIMARY KEY,
    direction       VARCHAR(10) NOT NULL,   -- inbound, outbound
    channel         VARCHAR(20) NOT NULL,   -- discord, signal, whatsapp, slack, asana, email
    sender          VARCHAR(200),
    recipient       VARCHAR(200),
    content         TEXT,
    is_morgan       BOOLEAN DEFAULT FALSE,
    thread_id       VARCHAR(200),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_myca_messages_channel ON myca_messages (channel);
CREATE INDEX IF NOT EXISTS idx_myca_messages_created ON myca_messages (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_myca_messages_morgan ON myca_messages (is_morgan) WHERE is_morgan = TRUE;

-- ════════════════════════════════════════════════════════════
-- 7. MYCA Files — File management index for VM 191
-- ════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS myca_files (
    id              BIGSERIAL PRIMARY KEY,
    file_path       VARCHAR(1000) NOT NULL,
    file_type       VARCHAR(50),            -- document, code, config, media, data
    category        VARCHAR(100),           -- project files, personal, system, etc.
    description     TEXT,
    size_bytes      BIGINT,
    checksum        VARCHAR(64),
    tags            TEXT[],
    last_modified   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(file_path)
);

CREATE INDEX IF NOT EXISTS idx_myca_files_type ON myca_files (file_type);
CREATE INDEX IF NOT EXISTS idx_myca_files_category ON myca_files (category);
CREATE INDEX IF NOT EXISTS idx_myca_files_tags ON myca_files USING gin (tags);

COMMIT;
