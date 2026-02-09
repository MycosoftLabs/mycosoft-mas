-- Migration: 015_system_registry.sql
-- Created: February 4, 2026
-- Purpose: System Registry tables for tracking all Mycosoft components

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Schema: registry
-- Purpose: System registry for APIs, agents, services, and devices
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS registry;

-- Systems table - top-level systems (MAS, Website, NatureOS, etc.)
CREATE TABLE IF NOT EXISTS registry.systems (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL,
    url VARCHAR(512),
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- APIs table - all API endpoints across systems
CREATE TABLE IF NOT EXISTS registry.apis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    system_id UUID REFERENCES registry.systems(id),
    path VARCHAR(512) NOT NULL,
    method VARCHAR(10) NOT NULL,
    description TEXT,
    tags VARCHAR(255)[],
    request_schema JSONB,
    response_schema JSONB,
    auth_required BOOLEAN DEFAULT FALSE,
    deprecated BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(system_id, path, method)
);

CREATE INDEX IF NOT EXISTS idx_apis_system ON registry.apis(system_id);
CREATE INDEX IF NOT EXISTS idx_apis_path ON registry.apis(path);
CREATE INDEX IF NOT EXISTS idx_apis_method ON registry.apis(method);

-- Agents table - all AI agents in the system
CREATE TABLE IF NOT EXISTS registry.agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL,
    description TEXT,
    capabilities VARCHAR(255)[],
    status VARCHAR(50) DEFAULT 'active',
    version VARCHAR(20),
    config JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agents_type ON registry.agents(type);
CREATE INDEX IF NOT EXISTS idx_agents_status ON registry.agents(status);

-- Services table - background services and workers
CREATE TABLE IF NOT EXISTS registry.services (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL,
    description TEXT,
    host VARCHAR(255),
    port INTEGER,
    status VARCHAR(50) DEFAULT 'unknown',
    health_endpoint VARCHAR(512),
    last_health_check TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_services_type ON registry.services(type);
CREATE INDEX IF NOT EXISTS idx_services_status ON registry.services(status);

-- Devices table - MycoBrain devices and hardware
CREATE TABLE IF NOT EXISTS registry.devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    firmware_version VARCHAR(50),
    hardware_version VARCHAR(50),
    status VARCHAR(50) DEFAULT 'unknown',
    last_seen TIMESTAMPTZ,
    config JSONB DEFAULT '{}',
    telemetry JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_devices_type ON registry.devices(type);
CREATE INDEX IF NOT EXISTS idx_devices_status ON registry.devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON registry.devices(last_seen DESC);

-- Code files table - indexed source code files
CREATE TABLE IF NOT EXISTS registry.code_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository VARCHAR(100) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    file_hash VARCHAR(64),
    line_count INTEGER,
    exports VARCHAR(255)[],
    imports VARCHAR(255)[],
    classes VARCHAR(255)[],
    functions VARCHAR(255)[],
    metadata JSONB DEFAULT '{}',
    indexed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(repository, file_path)
);

CREATE INDEX IF NOT EXISTS idx_code_repo ON registry.code_files(repository);
CREATE INDEX IF NOT EXISTS idx_code_type ON registry.code_files(file_type);

-- Integrations table - connections between systems
CREATE TABLE IF NOT EXISTS registry.integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_system UUID REFERENCES registry.systems(id),
    target_system UUID REFERENCES registry.systems(id),
    integration_type VARCHAR(50) NOT NULL,
    description TEXT,
    config JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_integrations_source ON registry.integrations(source_system);
CREATE INDEX IF NOT EXISTS idx_integrations_target ON registry.integrations(target_system);

-- =============================================================================
-- Triggers for updated_at
-- =============================================================================

CREATE OR REPLACE FUNCTION registry_update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_systems_timestamp') THEN
        CREATE TRIGGER update_systems_timestamp
            BEFORE UPDATE ON registry.systems
            FOR EACH ROW EXECUTE FUNCTION registry_update_timestamp();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_apis_timestamp') THEN
        CREATE TRIGGER update_apis_timestamp
            BEFORE UPDATE ON registry.apis
            FOR EACH ROW EXECUTE FUNCTION registry_update_timestamp();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_agents_timestamp') THEN
        CREATE TRIGGER update_agents_timestamp
            BEFORE UPDATE ON registry.agents
            FOR EACH ROW EXECUTE FUNCTION registry_update_timestamp();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_services_timestamp') THEN
        CREATE TRIGGER update_services_timestamp
            BEFORE UPDATE ON registry.services
            FOR EACH ROW EXECUTE FUNCTION registry_update_timestamp();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_devices_timestamp') THEN
        CREATE TRIGGER update_devices_timestamp
            BEFORE UPDATE ON registry.devices
            FOR EACH ROW EXECUTE FUNCTION registry_update_timestamp();
    END IF;
END $$;

-- =============================================================================
-- Initial data: Register core systems
-- =============================================================================

INSERT INTO registry.systems (name, description, type, url, status) VALUES
    ('MAS', 'Mycosoft Multi-Agent System Orchestrator', 'mas', 'http://192.168.0.188:8001', 'active'),
    ('Website', 'Mycosoft Website and Dashboard', 'website', 'http://192.168.0.187:3000', 'active'),
    ('MINDEX', 'Memory Index and Knowledge Graph Service', 'mindex', 'http://192.168.0.189:8000', 'active'),
    ('NatureOS', 'Nature Operating System Backend', 'natureos', 'http://192.168.0.188:5000', 'active'),
    ('MycoBrain', 'IoT Device Management System', 'mycobrain', 'http://192.168.0.188:8080', 'active'),
    ('NLM', 'Nature Learning Model Service', 'nlm', 'http://192.168.0.188:8200', 'active')
ON CONFLICT (name) DO UPDATE SET
    url = EXCLUDED.url,
    updated_at = NOW();

-- =============================================================================
-- Views
-- =============================================================================

CREATE OR REPLACE VIEW registry.v_active_apis AS
SELECT 
    a.id, a.path, a.method, a.description, a.tags,
    s.name as system_name, s.type as system_type, s.url as system_url
FROM registry.apis a
JOIN registry.systems s ON a.system_id = s.id
WHERE a.deprecated = FALSE AND s.status = 'active';

CREATE OR REPLACE VIEW registry.v_system_summary AS
SELECT 
    s.id, s.name, s.type, s.status, s.url,
    COUNT(DISTINCT a.id) as api_count,
    COUNT(DISTINCT ag.id) FILTER (WHERE ag.metadata->>'system' = s.name) as agent_count
FROM registry.systems s
LEFT JOIN registry.apis a ON a.system_id = s.id AND a.deprecated = FALSE
LEFT JOIN registry.agents ag ON ag.metadata->>'system' = s.name
GROUP BY s.id;
