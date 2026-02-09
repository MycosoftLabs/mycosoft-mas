-- Migration: 019b_gpu_memory.sql
-- GPU State Memory Tables - February 5, 2026
-- Tracks model loading events, VRAM usage, and enables preload optimization

-- ============================================================================
-- GPU Model Events Table
-- Records all model load/unload events for history and analysis
-- ============================================================================
CREATE TABLE IF NOT EXISTS mindex.gpu_model_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_type VARCHAR(50) NOT NULL DEFAULT 'custom',
    model_name VARCHAR(255) NOT NULL,
    event_type VARCHAR(20) NOT NULL DEFAULT 'load',
    vram_mb INTEGER NOT NULL DEFAULT 0,
    load_time_ms INTEGER NOT NULL DEFAULT 0,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    triggered_by VARCHAR(50) NOT NULL DEFAULT 'api'
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_gpu_model_events_timestamp 
    ON mindex.gpu_model_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_gpu_model_events_model_name 
    ON mindex.gpu_model_events(model_name);
CREATE INDEX IF NOT EXISTS idx_gpu_model_events_event_type 
    ON mindex.gpu_model_events(event_type);

-- ============================================================================
-- GPU VRAM Snapshots Table
-- Periodic snapshots of VRAM state for trend analysis
-- ============================================================================
CREATE TABLE IF NOT EXISTS mindex.gpu_vram_snapshots (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    total_vram_mb INTEGER NOT NULL DEFAULT 32768,
    used_vram_mb INTEGER NOT NULL DEFAULT 0,
    free_vram_mb INTEGER NOT NULL DEFAULT 32768,
    loaded_models JSONB NOT NULL DEFAULT '[]',
    utilization_percent REAL NOT NULL DEFAULT 0.0
);

CREATE INDEX IF NOT EXISTS idx_gpu_vram_snapshots_timestamp 
    ON mindex.gpu_vram_snapshots(timestamp DESC);

-- ============================================================================
-- GPU Model Usage Patterns Table
-- Learned usage patterns for intelligent preloading
-- ============================================================================
CREATE TABLE IF NOT EXISTS mindex.gpu_model_patterns (
    model_name VARCHAR(255) PRIMARY KEY,
    model_type VARCHAR(50) NOT NULL DEFAULT 'custom',
    total_loads INTEGER NOT NULL DEFAULT 0,
    total_inference_calls BIGINT NOT NULL DEFAULT 0,
    avg_load_time_ms REAL NOT NULL DEFAULT 0.0,
    avg_inference_time_ms REAL NOT NULL DEFAULT 0.0,
    hourly_usage JSONB NOT NULL DEFAULT '{}',
    daily_usage JSONB NOT NULL DEFAULT '{}',
    vram_mb INTEGER NOT NULL DEFAULT 0,
    last_used TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- GPU Inference Metrics Table
-- Detailed inference timing for performance analysis
-- ============================================================================
CREATE TABLE IF NOT EXISTS mindex.gpu_inference_metrics (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(255) NOT NULL,
    inference_time_ms INTEGER NOT NULL,
    input_size INTEGER,
    output_size INTEGER,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    success BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_gpu_inference_metrics_model 
    ON mindex.gpu_inference_metrics(model_name);
CREATE INDEX IF NOT EXISTS idx_gpu_inference_metrics_timestamp 
    ON mindex.gpu_inference_metrics(timestamp DESC);

-- ============================================================================
-- View: Current GPU State
-- Provides a summary of the current GPU state
-- ============================================================================
CREATE OR REPLACE VIEW mindex.gpu_current_state AS
SELECT 
    (SELECT MAX(timestamp) FROM mindex.gpu_vram_snapshots) as last_snapshot,
    (SELECT used_vram_mb FROM mindex.gpu_vram_snapshots ORDER BY timestamp DESC LIMIT 1) as current_used_mb,
    (SELECT free_vram_mb FROM mindex.gpu_vram_snapshots ORDER BY timestamp DESC LIMIT 1) as current_free_mb,
    (SELECT loaded_models FROM mindex.gpu_vram_snapshots ORDER BY timestamp DESC LIMIT 1) as loaded_models,
    (SELECT COUNT(*) FROM mindex.gpu_model_events WHERE timestamp > NOW() - INTERVAL '24 hours') as events_24h;

-- ============================================================================
-- View: Model Load Statistics
-- Aggregates model loading statistics
-- ============================================================================
CREATE OR REPLACE VIEW mindex.gpu_model_stats AS
SELECT 
    model_name,
    model_type,
    COUNT(*) FILTER (WHERE event_type = 'load') as load_count,
    COUNT(*) FILTER (WHERE event_type = 'unload') as unload_count,
    AVG(load_time_ms) FILTER (WHERE event_type = 'load') as avg_load_time_ms,
    MAX(vram_mb) as vram_mb,
    MAX(timestamp) as last_event,
    COUNT(*) FILTER (WHERE NOT success) as error_count
FROM mindex.gpu_model_events
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY model_name, model_type
ORDER BY load_count DESC;

-- ============================================================================
-- Function: Update model patterns on load event
-- ============================================================================
CREATE OR REPLACE FUNCTION mindex.update_gpu_model_pattern()
RETURNS TRIGGER AS $$
DECLARE
    current_hour INTEGER := EXTRACT(HOUR FROM NOW())::INTEGER;
    current_day TEXT := TO_CHAR(NOW(), 'Day');
    existing_hourly JSONB;
    existing_daily JSONB;
BEGIN
    IF NEW.event_type = 'load' AND NEW.success THEN
        -- Get existing patterns or create new
        SELECT hourly_usage, daily_usage INTO existing_hourly, existing_daily
        FROM mindex.gpu_model_patterns
        WHERE model_name = NEW.model_name;
        
        IF existing_hourly IS NULL THEN
            existing_hourly := '{}';
            existing_daily := '{}';
        END IF;
        
        -- Update hourly count
        existing_hourly := jsonb_set(
            existing_hourly, 
            ARRAY[current_hour::TEXT], 
            to_jsonb(COALESCE((existing_hourly->current_hour::TEXT)::INTEGER, 0) + 1)
        );
        
        -- Update daily count
        existing_daily := jsonb_set(
            existing_daily, 
            ARRAY[TRIM(current_day)], 
            to_jsonb(COALESCE((existing_daily->TRIM(current_day))::INTEGER, 0) + 1)
        );
        
        INSERT INTO mindex.gpu_model_patterns 
            (model_name, model_type, total_loads, avg_load_time_ms, hourly_usage, daily_usage, vram_mb, last_used)
        VALUES 
            (NEW.model_name, NEW.model_type, 1, NEW.load_time_ms, existing_hourly, existing_daily, NEW.vram_mb, NOW())
        ON CONFLICT (model_name) DO UPDATE SET
            total_loads = mindex.gpu_model_patterns.total_loads + 1,
            avg_load_time_ms = (mindex.gpu_model_patterns.avg_load_time_ms * mindex.gpu_model_patterns.total_loads + NEW.load_time_ms) / (mindex.gpu_model_patterns.total_loads + 1),
            hourly_usage = existing_hourly,
            daily_usage = existing_daily,
            vram_mb = NEW.vram_mb,
            last_used = NOW(),
            updated_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update patterns on model event
DROP TRIGGER IF EXISTS trg_gpu_model_pattern ON mindex.gpu_model_events;
CREATE TRIGGER trg_gpu_model_pattern
    AFTER INSERT ON mindex.gpu_model_events
    FOR EACH ROW
    EXECUTE FUNCTION mindex.update_gpu_model_pattern();

-- ============================================================================
-- Comments for documentation
-- ============================================================================
COMMENT ON TABLE mindex.gpu_model_events IS 'Model load/unload event history';
COMMENT ON TABLE mindex.gpu_vram_snapshots IS 'Periodic VRAM state snapshots';
COMMENT ON TABLE mindex.gpu_model_patterns IS 'Learned model usage patterns for preloading';
COMMENT ON TABLE mindex.gpu_inference_metrics IS 'Inference timing metrics';
COMMENT ON VIEW mindex.gpu_current_state IS 'Current GPU state summary';
COMMENT ON VIEW mindex.gpu_model_stats IS 'Model loading statistics';