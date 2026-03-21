-- Migration: 026_serving_registry.sql
-- Date: 2026-03-21
-- Description: Serving profile table for versioned serving configurations
-- Part of: Plasticity Forge Phase 1 — KVTC Serving Lane

CREATE TABLE IF NOT EXISTS serving_profile (
    serving_profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_build_id UUID NOT NULL,
    profile_name TEXT NOT NULL,
    cache_mode TEXT NOT NULL DEFAULT 'baseline',
    -- cache_mode: 'baseline', 'kvtc8x', 'kvtc16x', 'kvtc32x', 'hybrid_attention_only'
    hot_window_tokens INTEGER NOT NULL DEFAULT 128,
    sink_tokens INTEGER NOT NULL DEFAULT 4,
    rope_handling TEXT,
    attention_only BOOLEAN NOT NULL DEFAULT FALSE,
    mla_latent_mode BOOLEAN NOT NULL DEFAULT FALSE,
    offload_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
    transport_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
    target_stack TEXT NOT NULL,
    -- target_stack: 'vllm', 'lmcache', 'megatron', 'custom'
    artifact_ref UUID,
    edge_eligible BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL DEFAULT 'draft',
    -- status: 'draft', 'calibrating', 'ready', 'shadow', 'canary', 'active', 'retired'
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_serving_profile_model ON serving_profile(model_build_id);
CREATE INDEX IF NOT EXISTS idx_serving_profile_status ON serving_profile(status);
