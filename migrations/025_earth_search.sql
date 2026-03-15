-- Earth Search — planetary-scale unified search schema
-- Stores all ingested search results from every domain (species, environment,
-- infrastructure, space, climate, telecom, sensors, science) for local low-latency
-- re-query and NLM training data.
--
-- Tables:
--   earth_search_results — individual search result records with geospatial indexing
--   earth_search_queries — search query audit log for analytics and training
--   earth_search_sources — data source health and last-sync tracking
--
-- Created: March 15, 2026

-- ──────────────────────────────────────────────────────────────────────────────
-- 1. Earth Search Results
-- ──────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS earth_search_results (
    id              BIGSERIAL PRIMARY KEY,
    result_id       TEXT NOT NULL UNIQUE,
    domain          TEXT NOT NULL,            -- EarthSearchDomain enum value
    source          TEXT NOT NULL,            -- data source ID (e.g. "inaturalist", "usgs_earthquake")
    title           TEXT NOT NULL,
    description     TEXT DEFAULT '',
    data            JSONB DEFAULT '{}',       -- full result payload
    lat             DOUBLE PRECISION,
    lng             DOUBLE PRECISION,
    "timestamp"     TIMESTAMPTZ,              -- event/observation time
    confidence      DOUBLE PRECISION DEFAULT 0.5,
    crep_layer      TEXT,                     -- CREP map layer name
    crep_entity_id  TEXT,                     -- CREP entity ID for map interaction
    mindex_id       TEXT,                     -- local MINDEX record ID
    url             TEXT,
    image_url       TEXT,
    query           TEXT,                     -- original search query
    session_id      TEXT,
    user_id         TEXT,
    ingested_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast lookup
CREATE INDEX IF NOT EXISTS idx_esr_domain ON earth_search_results (domain);
CREATE INDEX IF NOT EXISTS idx_esr_source ON earth_search_results (source);
CREATE INDEX IF NOT EXISTS idx_esr_crep_layer ON earth_search_results (crep_layer);
CREATE INDEX IF NOT EXISTS idx_esr_timestamp ON earth_search_results ("timestamp" DESC);
CREATE INDEX IF NOT EXISTS idx_esr_ingested ON earth_search_results (ingested_at DESC);
CREATE INDEX IF NOT EXISTS idx_esr_query ON earth_search_results USING gin (to_tsvector('english', query));
CREATE INDEX IF NOT EXISTS idx_esr_title ON earth_search_results USING gin (to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_esr_data ON earth_search_results USING gin (data);

-- Geospatial index (if PostGIS extension available)
-- CREATE INDEX IF NOT EXISTS idx_esr_geo ON earth_search_results USING gist (
--     ST_SetSRID(ST_MakePoint(lng, lat), 4326)
-- );
-- Fallback: simple numeric range index for lat/lng queries
CREATE INDEX IF NOT EXISTS idx_esr_lat ON earth_search_results (lat);
CREATE INDEX IF NOT EXISTS idx_esr_lng ON earth_search_results (lng);

-- ──────────────────────────────────────────────────────────────────────────────
-- 2. Earth Search Queries (audit / analytics / training)
-- ──────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS earth_search_queries (
    id              BIGSERIAL PRIMARY KEY,
    query           TEXT NOT NULL,
    domains         TEXT[] DEFAULT '{}',      -- domains searched
    domain_groups   TEXT[] DEFAULT '{}',      -- domain groups requested
    result_count    INTEGER DEFAULT 0,
    sources_queried TEXT[] DEFAULT '{}',
    duration_ms     DOUBLE PRECISION,
    has_geo         BOOLEAN DEFAULT FALSE,
    geo_lat         DOUBLE PRECISION,
    geo_lng         DOUBLE PRECISION,
    geo_radius_km   DOUBLE PRECISION,
    user_id         TEXT,
    session_id      TEXT,
    llm_answer      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_esq_query ON earth_search_queries USING gin (to_tsvector('english', query));
CREATE INDEX IF NOT EXISTS idx_esq_created ON earth_search_queries (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_esq_user ON earth_search_queries (user_id);

-- ──────────────────────────────────────────────────────────────────────────────
-- 3. Earth Search Data Sources (health tracking)
-- ──────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS earth_search_sources (
    source_id       TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    api_url         TEXT,
    domains         TEXT[] DEFAULT '{}',
    requires_key    BOOLEAN DEFAULT FALSE,
    is_realtime     BOOLEAN DEFAULT FALSE,
    last_success    TIMESTAMPTZ,
    last_failure    TIMESTAMPTZ,
    failure_count   INTEGER DEFAULT 0,
    total_results   BIGINT DEFAULT 0,
    status          TEXT DEFAULT 'unknown',    -- healthy, degraded, down, unknown
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ──────────────────────────────────────────────────────────────────────────────
-- 4. Updated trigger for updated_at
-- ──────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_earth_search_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_esr_updated ON earth_search_results;
CREATE TRIGGER trg_esr_updated
    BEFORE UPDATE ON earth_search_results
    FOR EACH ROW EXECUTE FUNCTION update_earth_search_updated_at();

DROP TRIGGER IF EXISTS trg_ess_updated ON earth_search_sources;
CREATE TRIGGER trg_ess_updated
    BEFORE UPDATE ON earth_search_sources
    FOR EACH ROW EXECUTE FUNCTION update_earth_search_updated_at();
