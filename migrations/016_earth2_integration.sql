-- Earth-2 Integration Schema Migration
-- February 4, 2026
-- Migration: 016_earth2_integration.sql

-- Create earth2 schema
CREATE SCHEMA IF NOT EXISTS earth2;

-- ============================================================================
-- Model Runs Table - Track all Earth-2 model executions
-- ============================================================================
CREATE TABLE IF NOT EXISTS earth2.model_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model VARCHAR(100) NOT NULL,
    run_type VARCHAR(50) NOT NULL CHECK (run_type IN ('forecast', 'nowcast', 'downscale', 'assimilation', 'spore_dispersal')),
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    
    -- Request info
    requested_by VARCHAR(255) DEFAULT 'system',
    request_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Spatial extent (nullable for global runs)
    min_lat REAL,
    max_lat REAL,
    min_lon REAL,
    max_lon REAL,
    
    -- Time range
    time_start TIMESTAMPTZ,
    time_end TIMESTAMPTZ,
    time_step_hours INTEGER,
    
    -- Provenance
    model_version VARCHAR(100),
    input_data_source VARCHAR(255),
    input_data_timestamp TIMESTAMPTZ,
    gpu_device VARCHAR(50),
    
    -- Results
    output_path TEXT,
    error_message TEXT,
    
    -- Metrics
    compute_time_seconds REAL,
    gpu_memory_peak_mb REAL,
    output_size_mb REAL,
    
    -- Timestamps
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for model runs
CREATE INDEX IF NOT EXISTS idx_earth2_runs_model ON earth2.model_runs(model);
CREATE INDEX IF NOT EXISTS idx_earth2_runs_type ON earth2.model_runs(run_type);
CREATE INDEX IF NOT EXISTS idx_earth2_runs_status ON earth2.model_runs(status);
CREATE INDEX IF NOT EXISTS idx_earth2_runs_timestamp ON earth2.model_runs(request_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_earth2_runs_spatial ON earth2.model_runs(min_lat, max_lat, min_lon, max_lon);

-- ============================================================================
-- Forecasts Table - Store forecast outputs
-- ============================================================================
CREATE TABLE IF NOT EXISTS earth2.forecasts (
    forecast_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES earth2.model_runs(run_id) ON DELETE CASCADE,
    
    -- Forecast metadata
    variable VARCHAR(50) NOT NULL,
    pressure_level INTEGER,
    timestamp TIMESTAMPTZ NOT NULL,
    
    -- Data location
    data_url TEXT NOT NULL,
    data_format VARCHAR(50) DEFAULT 'zarr',
    
    -- Statistics
    min_value REAL,
    max_value REAL,
    mean_value REAL,
    std_value REAL,
    units VARCHAR(50),
    
    -- Data shape
    lat_size INTEGER,
    lon_size INTEGER,
    
    -- Ensemble info (for ensemble forecasts)
    ensemble_member INTEGER,
    ensemble_total INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for forecasts
CREATE INDEX IF NOT EXISTS idx_earth2_forecasts_run ON earth2.forecasts(run_id);
CREATE INDEX IF NOT EXISTS idx_earth2_forecasts_variable ON earth2.forecasts(variable);
CREATE INDEX IF NOT EXISTS idx_earth2_forecasts_timestamp ON earth2.forecasts(timestamp);

-- ============================================================================
-- Nowcasts Table - Store nowcast outputs
-- ============================================================================
CREATE TABLE IF NOT EXISTS earth2.nowcasts (
    nowcast_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES earth2.model_runs(run_id) ON DELETE CASCADE,
    
    -- Nowcast metadata
    product_type VARCHAR(50) NOT NULL CHECK (product_type IN ('satellite', 'radar', 'composite')),
    timestamp TIMESTAMPTZ NOT NULL,
    
    -- Data location
    data_url TEXT NOT NULL,
    data_format VARCHAR(50) DEFAULT 'zarr',
    
    -- Confidence and hazards
    confidence REAL CHECK (confidence >= 0 AND confidence <= 1),
    hazard_flags JSONB DEFAULT '[]'::jsonb,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for nowcasts
CREATE INDEX IF NOT EXISTS idx_earth2_nowcasts_run ON earth2.nowcasts(run_id);
CREATE INDEX IF NOT EXISTS idx_earth2_nowcasts_timestamp ON earth2.nowcasts(timestamp);
CREATE INDEX IF NOT EXISTS idx_earth2_nowcasts_product ON earth2.nowcasts(product_type);

-- ============================================================================
-- Assimilation Runs Table - Track data assimilation
-- ============================================================================
CREATE TABLE IF NOT EXISTS earth2.assimilation_runs (
    assimilation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES earth2.model_runs(run_id) ON DELETE CASCADE,
    
    -- Input data
    background_data_path TEXT NOT NULL,
    observations_count INTEGER NOT NULL,
    
    -- Results
    observations_assimilated INTEGER,
    analysis_increment_rms JSONB,
    
    -- Output
    analysis_data_path TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Downscaled Products Table - Store high-res regional outputs
-- ============================================================================
CREATE TABLE IF NOT EXISTS earth2.downscaled_products (
    product_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES earth2.model_runs(run_id) ON DELETE CASCADE,
    
    -- Resolution info
    input_resolution REAL NOT NULL,
    output_resolution REAL NOT NULL,
    
    -- Performance metrics
    speedup_factor REAL,
    energy_efficiency REAL,
    
    -- Data location
    data_path TEXT NOT NULL,
    
    -- Output dimensions
    output_lat_size INTEGER,
    output_lon_size INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Spore Dispersal Table - Combined weather + MINDEX results
-- ============================================================================
CREATE TABLE IF NOT EXISTS earth2.spore_dispersal (
    dispersal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES earth2.model_runs(run_id) ON DELETE CASCADE,
    weather_run_id UUID REFERENCES earth2.model_runs(run_id),
    
    -- Parameters
    species_filter JSONB,
    source_locations JSONB,
    include_precipitation BOOLEAN DEFAULT TRUE,
    include_humidity BOOLEAN DEFAULT TRUE,
    
    -- Results
    concentration_map_url TEXT,
    risk_zones JSONB DEFAULT '[]'::jsonb,
    peak_concentration_time TIMESTAMPTZ,
    affected_area_km2 REAL,
    
    -- MINDEX integration
    mindex_species_matched JSONB DEFAULT '[]'::jsonb,
    mindex_observations_used INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Visualization Layers Table - Map layers for CREP/Earth Simulator
-- ============================================================================
CREATE TABLE IF NOT EXISTS earth2.visualization_layers (
    layer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES earth2.model_runs(run_id) ON DELETE CASCADE,
    
    -- Layer metadata
    layer_type VARCHAR(50) NOT NULL,
    layer_name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Tile service info
    tile_url_template TEXT,
    min_zoom INTEGER DEFAULT 0,
    max_zoom INTEGER DEFAULT 18,
    
    -- Time range
    valid_start TIMESTAMPTZ,
    valid_end TIMESTAMPTZ,
    
    -- Styling
    color_map VARCHAR(100),
    opacity REAL DEFAULT 1.0,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for visualization layers
CREATE INDEX IF NOT EXISTS idx_earth2_layers_run ON earth2.visualization_layers(run_id);
CREATE INDEX IF NOT EXISTS idx_earth2_layers_type ON earth2.visualization_layers(layer_type);
CREATE INDEX IF NOT EXISTS idx_earth2_layers_active ON earth2.visualization_layers(is_active);

-- ============================================================================
-- Functions
-- ============================================================================

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION earth2.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to model_runs
DROP TRIGGER IF EXISTS trigger_earth2_runs_updated ON earth2.model_runs;
CREATE TRIGGER trigger_earth2_runs_updated
    BEFORE UPDATE ON earth2.model_runs
    FOR EACH ROW
    EXECUTE FUNCTION earth2.update_updated_at();

-- ============================================================================
-- Views
-- ============================================================================

-- Active forecasts view
CREATE OR REPLACE VIEW earth2.active_forecasts AS
SELECT 
    r.run_id,
    r.model,
    r.status,
    r.request_timestamp,
    r.min_lat, r.max_lat, r.min_lon, r.max_lon,
    r.time_start, r.time_end,
    COUNT(f.forecast_id) AS output_count,
    r.compute_time_seconds,
    r.output_path
FROM earth2.model_runs r
LEFT JOIN earth2.forecasts f ON r.run_id = f.run_id
WHERE r.run_type = 'forecast'
  AND r.completed_at > NOW() - INTERVAL '7 days'
GROUP BY r.run_id;

-- Recent spore alerts view
CREATE OR REPLACE VIEW earth2.recent_spore_alerts AS
SELECT 
    s.dispersal_id,
    r.run_id,
    r.request_timestamp,
    r.min_lat, r.max_lat, r.min_lon, r.max_lon,
    s.peak_concentration_time,
    s.affected_area_km2,
    s.risk_zones,
    s.mindex_species_matched
FROM earth2.spore_dispersal s
JOIN earth2.model_runs r ON s.run_id = r.run_id
WHERE r.status = 'completed'
  AND r.completed_at > NOW() - INTERVAL '24 hours'
ORDER BY r.completed_at DESC;

-- ============================================================================
-- Comments
-- ============================================================================
COMMENT ON SCHEMA earth2 IS 'NVIDIA Earth-2 AI weather model integration';
COMMENT ON TABLE earth2.model_runs IS 'All Earth-2 model executions with provenance';
COMMENT ON TABLE earth2.forecasts IS 'Medium-range forecast outputs from Atlas model';
COMMENT ON TABLE earth2.nowcasts IS 'Short-range nowcast outputs from StormScope model';
COMMENT ON TABLE earth2.assimilation_runs IS 'Data assimilation runs from HealDA model';
COMMENT ON TABLE earth2.downscaled_products IS 'High-resolution downscaled outputs from CorrDiff';
COMMENT ON TABLE earth2.spore_dispersal IS 'Spore dispersal forecasts combining weather + MINDEX';
COMMENT ON TABLE earth2.visualization_layers IS 'Map layers for CREP and Earth Simulator';
