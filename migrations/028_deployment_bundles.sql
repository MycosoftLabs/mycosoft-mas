-- Migration: 028_deployment_bundles.sql
-- Date: 2026-03-21
-- Description: Deployment bundle and serving eval tables
-- Part of: Plasticity Forge Phase 1 — KVTC Serving Lane

CREATE TABLE IF NOT EXISTS deployment_bundle (
    deployment_bundle_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_build_id UUID NOT NULL,
    adapter_set_id UUID,
    serving_profile_id UUID NOT NULL REFERENCES serving_profile(serving_profile_id),
    cache_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
    target_alias TEXT NOT NULL,
    -- target_alias: 'myca_core', 'myca_edge', 'avani_core', 'fallback_local'
    target_runtime TEXT NOT NULL,
    rollout_state TEXT NOT NULL DEFAULT 'shadow',
    -- rollout_state: 'shadow', 'canary', 'active', 'rollback', 'retired'
    rollback_bundle_id UUID REFERENCES deployment_bundle(deployment_bundle_id),
    promoted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_deployment_bundle_alias ON deployment_bundle(target_alias);
CREATE INDEX IF NOT EXISTS idx_deployment_bundle_state ON deployment_bundle(rollout_state);

CREATE TABLE IF NOT EXISTS serving_eval_run (
    serving_eval_run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deployment_bundle_id UUID NOT NULL REFERENCES deployment_bundle(deployment_bundle_id),
    eval_suite TEXT NOT NULL,
    ttft_ms_p50 NUMERIC,
    ttft_ms_p95 NUMERIC,
    cache_hit_rate NUMERIC,
    recomputation_rate NUMERIC,
    hbm_bytes_saved BIGINT,
    warm_bytes_saved BIGINT,
    transfer_bytes_saved BIGINT,
    compression_ratio_actual NUMERIC,
    task_success_delta NUMERIC,
    tool_validity_delta NUMERIC,
    hallucination_delta NUMERIC,
    long_context_score NUMERIC,
    regression_verdict TEXT,
    -- regression_verdict: 'pass', 'warn', 'fail'
    raw_results JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_serving_eval_bundle ON serving_eval_run(deployment_bundle_id);
