-- Migration: 019_earth2_memory.sql
-- Earth2 Weather AI Memory Tables - February 5, 2026
-- Stores forecast results, user preferences, and model usage for Earth2Studio integration

-- ============================================================================
-- Earth2 Forecasts Table
-- Stores individual forecast results for recall and analysis
-- ============================================================================
CREATE TABLE IF NOT EXISTS mindex.earth2_forecasts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    model VARCHAR(50) NOT NULL DEFAULT 'fcn',
    location JSONB NOT NULL DEFAULT '{}',
    location_name VARCHAR(255),
    lead_time_hours INTEGER NOT NULL DEFAULT 24,
    variables JSONB NOT NULL DEFAULT '[]',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    result_summary JSONB,
    inference_time_ms INTEGER,
    source VARCHAR(50) NOT NULL DEFAULT 'api',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_earth2_forecasts_user_id 
    ON mindex.earth2_forecasts(user_id);
CREATE INDEX IF NOT EXISTS idx_earth2_forecasts_timestamp 
    ON mindex.earth2_forecasts(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_earth2_forecasts_model 
    ON mindex.earth2_forecasts(model);
CREATE INDEX IF NOT EXISTS idx_earth2_forecasts_location 
    ON mindex.earth2_forecasts USING GIN(location);

-- ============================================================================
-- Earth2 User Preferences Table
-- Stores learned user preferences for weather forecasts
-- ============================================================================
CREATE TABLE IF NOT EXISTS mindex.earth2_user_preferences (
    user_id VARCHAR(255) PRIMARY KEY,
    favorite_locations JSONB NOT NULL DEFAULT '[]',
    preferred_models JSONB NOT NULL DEFAULT '[]',
    common_lead_times JSONB NOT NULL DEFAULT '[]',
    variables_of_interest JSONB NOT NULL DEFAULT '[]',
    forecast_frequency INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- Earth2 Model Usage Table
-- Tracks model usage statistics for optimization
-- ============================================================================
CREATE TABLE IF NOT EXISTS mindex.earth2_model_usage (
    id SERIAL PRIMARY KEY,
    model VARCHAR(50) NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    total_runs INTEGER NOT NULL DEFAULT 0,
    total_inference_time_ms BIGINT NOT NULL DEFAULT 0,
    avg_inference_time_ms REAL NOT NULL DEFAULT 0.0,
    error_count INTEGER NOT NULL DEFAULT 0,
    vram_mb INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(model, date)
);

CREATE INDEX IF NOT EXISTS idx_earth2_model_usage_date 
    ON mindex.earth2_model_usage(date DESC);

-- ============================================================================
-- Earth2 Popular Locations View
-- Aggregates popular forecast locations for suggestions
-- ============================================================================
CREATE OR REPLACE VIEW mindex.earth2_popular_locations AS
SELECT 
    location_name,
    location,
    COUNT(*) as forecast_count,
    MAX(timestamp) as last_forecast
FROM mindex.earth2_forecasts
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY location_name, location
ORDER BY forecast_count DESC
LIMIT 50;

-- ============================================================================
-- Function: Update model usage on forecast
-- ============================================================================
CREATE OR REPLACE FUNCTION mindex.update_earth2_model_usage()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO mindex.earth2_model_usage (model, date, total_runs, total_inference_time_ms, vram_mb)
    VALUES (NEW.model, CURRENT_DATE, 1, COALESCE(NEW.inference_time_ms, 0), 0)
    ON CONFLICT (model, date) DO UPDATE SET
        total_runs = mindex.earth2_model_usage.total_runs + 1,
        total_inference_time_ms = mindex.earth2_model_usage.total_inference_time_ms + COALESCE(NEW.inference_time_ms, 0),
        avg_inference_time_ms = (mindex.earth2_model_usage.total_inference_time_ms + COALESCE(NEW.inference_time_ms, 0))::REAL / (mindex.earth2_model_usage.total_runs + 1),
        updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update usage stats on forecast insert
DROP TRIGGER IF EXISTS trg_earth2_forecast_usage ON mindex.earth2_forecasts;
CREATE TRIGGER trg_earth2_forecast_usage
    AFTER INSERT ON mindex.earth2_forecasts
    FOR EACH ROW
    EXECUTE FUNCTION mindex.update_earth2_model_usage();

-- ============================================================================
-- Comments for documentation
-- ============================================================================
COMMENT ON TABLE mindex.earth2_forecasts IS 'Individual Earth2 weather forecast results';
COMMENT ON TABLE mindex.earth2_user_preferences IS 'Learned user preferences for weather forecasts';
COMMENT ON TABLE mindex.earth2_model_usage IS 'Daily model usage statistics for optimization';
COMMENT ON VIEW mindex.earth2_popular_locations IS 'Aggregated popular forecast locations';