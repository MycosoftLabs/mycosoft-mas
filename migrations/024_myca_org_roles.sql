-- MYCA Org Roles and Standup — assigned_to, daily standup digests, Beto onboarding
-- Run on MINDEX PostgreSQL (192.168.0.189:5432, database: mycosoft_mas)
-- Date: 2026-03-05

BEGIN;

-- Add assigned_to to myca_task_queue for role-scoped task routing
ALTER TABLE myca_task_queue
  ADD COLUMN IF NOT EXISTS assigned_to VARCHAR(50);

CREATE INDEX IF NOT EXISTS idx_myca_tasks_assigned_to ON myca_task_queue (assigned_to) WHERE assigned_to IS NOT NULL;

-- Daily standup digests — stored after standup collection
CREATE TABLE IF NOT EXISTS myca_daily_standup_digests (
    id              BIGSERIAL PRIMARY KEY,
    digest_date     DATE NOT NULL UNIQUE,
    summary         TEXT,
    responses       JSONB DEFAULT '{}',
    overdue_items   JSONB DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_standup_digest_date ON myca_daily_standup_digests (digest_date DESC);

-- Beto onboarding progress — MYCA tracks completion
CREATE TABLE IF NOT EXISTS myca_beto_onboarding (
    id              BIGSERIAL PRIMARY KEY,
    checklist_id    VARCHAR(50) NOT NULL,
    completed_at    TIMESTAMPTZ,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(checklist_id)
);

CREATE INDEX IF NOT EXISTS idx_beto_onboarding_checklist ON myca_beto_onboarding (checklist_id);

COMMIT;
