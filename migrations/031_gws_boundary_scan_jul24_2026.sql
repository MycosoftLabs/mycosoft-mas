-- Google Workspace CUI-boundary scan state — metadata only.
-- No file names, message subjects, bodies, snippets, or credentials are stored.

CREATE TABLE IF NOT EXISTS soc_ops.gws_boundary_scan_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status TEXT NOT NULL CHECK (status IN ('clean', 'hits', 'error')),
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL,
    scanned_scope JSONB NOT NULL DEFAULT '[]'::jsonb,
    hit_count INTEGER NOT NULL DEFAULT 0 CHECK (hit_count >= 0),
    error_code TEXT,
    notification_status TEXT NOT NULL DEFAULT 'not-required',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gws_boundary_scan_runs_completed
    ON soc_ops.gws_boundary_scan_runs (completed_at DESC);

CREATE TABLE IF NOT EXISTS soc_ops.gws_boundary_scan_hits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES soc_ops.gws_boundary_scan_runs(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    container TEXT NOT NULL,
    item_id TEXT NOT NULL,
    owner TEXT NOT NULL,
    marking_token TEXT NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_gws_boundary_scan_hits_run
    ON soc_ops.gws_boundary_scan_hits (run_id, detected_at DESC);
