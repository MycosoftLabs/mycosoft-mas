-- Migration: 027_kvtc_artifacts.sql
-- Date: 2026-03-21
-- Description: KVTC calibration artifact storage
-- Part of: Plasticity Forge Phase 1 — KVTC Serving Lane

CREATE TABLE IF NOT EXISTS kvtc_artifact (
    kvtc_artifact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_build_id UUID NOT NULL,
    compression_target TEXT NOT NULL,
    -- compression_target: '8x', '16x', '32x', '64x'
    vk_uri TEXT NOT NULL,
    vv_uri TEXT NOT NULL,
    muk_uri TEXT NOT NULL,
    muv_uri TEXT NOT NULL,
    key_bitplan JSONB NOT NULL,
    value_bitplan JSONB NOT NULL,
    pca_rank INTEGER,
    calibration_tokens INTEGER,
    rope_undo_required BOOLEAN NOT NULL DEFAULT FALSE,
    attention_only BOOLEAN NOT NULL DEFAULT FALSE,
    mla_latent_mode BOOLEAN NOT NULL DEFAULT FALSE,
    calibration_dataset_hash TEXT NOT NULL,
    artifact_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_kvtc_artifact_model ON kvtc_artifact(model_build_id);
CREATE INDEX IF NOT EXISTS idx_kvtc_artifact_target ON kvtc_artifact(compression_target);
