-- Personnel screening + SSP evidence spine (Perplexity handoff patch v2, Jul 21 2026)
-- Schema: soc_ops (MINDEX Postgres 189)

CREATE TABLE IF NOT EXISTS soc_ops.ps_subject (
    subject_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    legal_name TEXT NOT NULL,
    role TEXT NOT NULL,
    cui_access BOOL NOT NULL DEFAULT true,
    fcra_disclosure_signed_at TIMESTAMPTZ,
    fcra_authorization_signed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS soc_ops.ps_screening_event (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id UUID NOT NULL REFERENCES soc_ops.ps_subject(subject_id),
    provider TEXT NOT NULL,
    package TEXT NOT NULL,
    ordered_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    report_preveil_path TEXT,
    report_drive_file_id TEXT,
    adjudicator_subject_id UUID REFERENCES soc_ops.ps_subject(subject_id),
    adjudication_memo_preveil_path TEXT,
    adjudication_memo_drive_file_id TEXT,
    adjudication_memo_id TEXT,
    disposition TEXT NOT NULL CHECK (disposition IN ('cleared', 'cleared_with_condition', 'denied', 'pending')),
    next_review_due_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT no_self_adjudication CHECK (
        adjudicator_subject_id IS NULL OR subject_id != adjudicator_subject_id
    )
);

CREATE INDEX IF NOT EXISTS idx_ps_screening_event_subject
    ON soc_ops.ps_screening_event (subject_id, completed_at DESC);

CREATE TABLE IF NOT EXISTS soc_ops.ssp_evidence (
    evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    control_ids TEXT[] NOT NULL,
    evidence_type TEXT NOT NULL,
    artifact_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    actor_subject_id UUID REFERENCES soc_ops.ps_subject(subject_id),
    verified_at TIMESTAMPTZ NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ssp_evidence_created
    ON soc_ops.ssp_evidence (created_at DESC);

CREATE TABLE IF NOT EXISTS soc_ops.compliance_audit_log (
    id BIGSERIAL PRIMARY KEY,
    operator TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    purpose TEXT NOT NULL,
    evidence_id UUID REFERENCES soc_ops.ssp_evidence(evidence_id),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_compliance_audit_log_created
    ON soc_ops.compliance_audit_log (created_at DESC);

-- Seed Morgan + RJ subjects and Jul 21 HireRight screening events (metadata only; no CUI bodies).
INSERT INTO soc_ops.ps_subject (subject_id, legal_name, role, cui_access)
VALUES
    ('11111111-1111-4111-8111-111111111101'::uuid, 'Rockcoons, Morgan', 'Founder & CEO', true),
    ('11111111-1111-4111-8111-111111111102'::uuid, 'Ricasata, Raljoseph', 'CFO', true)
ON CONFLICT (subject_id) DO NOTHING;

INSERT INTO soc_ops.ps_screening_event (
    event_id,
    subject_id,
    provider,
    package,
    ordered_at,
    completed_at,
    report_preveil_path,
    report_drive_file_id,
    adjudicator_subject_id,
    adjudication_memo_preveil_path,
    adjudication_memo_drive_file_id,
    adjudication_memo_id,
    disposition,
    next_review_due_at
)
VALUES
    (
        '22222222-2222-4222-8222-222222222201'::uuid,
        '11111111-1111-4111-8111-111111111101'::uuid,
        'HireRight',
        '6-check standard',
        '2026-07-20T00:00:00+00:00'::timestamptz,
        '2026-07-21T00:00:00+00:00'::timestamptz,
        '/CUI/Personnel-Screening/11111111-1111-4111-8111-111111111101/Rockcoons_Morgan_BGC_2026-07-21.pdf',
        '1DQqQ_9oem2tirjZoi5g9PBl7Q4_tQSPz',
        '11111111-1111-4111-8111-111111111102'::uuid,
        '/CUI/Personnel-Screening/11111111-1111-4111-8111-111111111101/adjudication_memo_rockcoons.pdf',
        '1C4qrjB-YVeHw5DrDmdwtGqFaTSa8-np5',
        'MYC-ADJ-ROCKCOONS-2026-07-21',
        'cleared',
        '2029-07-21T00:00:00+00:00'::timestamptz
    ),
    (
        '22222222-2222-4222-8222-222222222202'::uuid,
        '11111111-1111-4111-8111-111111111102'::uuid,
        'HireRight',
        '6-check standard',
        '2026-07-20T00:00:00+00:00'::timestamptz,
        '2026-07-21T00:00:00+00:00'::timestamptz,
        '/CUI/Personnel-Screening/11111111-1111-4111-8111-111111111102/Ricasata_Raljoseph_BGC_2026-07-21.pdf',
        '1FrI9D4pdXvdtChEugCMCn7709Dee74Hn',
        '11111111-1111-4111-8111-111111111101'::uuid,
        '/CUI/Personnel-Screening/11111111-1111-4111-8111-111111111102/adjudication_memo_ricasata.pdf',
        '1t6VaX6Oj011Mf5ovO65sv7sWXzYGtXOr',
        'MYC-ADJ-RICASATA-2026-07-21',
        'cleared',
        '2029-07-21T00:00:00+00:00'::timestamptz
    )
ON CONFLICT (event_id) DO NOTHING;

COMMENT ON TABLE soc_ops.ps_subject IS 'Personnel screening subjects (CUI handlers); metadata only in Postgres';
COMMENT ON TABLE soc_ops.ps_screening_event IS 'Screening/adjudication cycles; PreVeil paths authoritative, Drive IDs are working mirror';
COMMENT ON TABLE soc_ops.ssp_evidence IS 'Append-only SSP evidence bundles (WORM intent — no UPDATE/DELETE in app layer)';
