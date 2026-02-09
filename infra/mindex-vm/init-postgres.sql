-- MINDEX PostgreSQL Initialization Script
-- Created: February 4, 2026
-- Purpose: Initialize all schemas for Memory Index, Ledger, Registry, and Knowledge Graph

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- Schema: memory
-- Purpose: Unified memory storage for all scopes
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS memory;

-- Memory entries table
CREATE TABLE IF NOT EXISTS memory.entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scope VARCHAR(50) NOT NULL,
    namespace VARCHAR(255) NOT NULL,
    key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    data_hash VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    version INTEGER DEFAULT 1,
    UNIQUE(scope, namespace, key)
);

CREATE INDEX IF NOT EXISTS idx_memory_scope ON memory.entries(scope);
CREATE INDEX IF NOT EXISTS idx_memory_namespace ON memory.entries(namespace);
CREATE INDEX IF NOT EXISTS idx_memory_key ON memory.entries(key);
CREATE INDEX IF NOT EXISTS idx_memory_expires ON memory.entries(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_memory_created ON memory.entries(created_at DESC);

-- Audit log table
CREATE TABLE IF NOT EXISTS memory.audit_log (
    entry_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    user_id VARCHAR(255) NOT NULL,
    action VARCHAR(255) NOT NULL,
    resource VARCHAR(512) NOT NULL,
    details JSONB DEFAULT '{}',
    ip_address VARCHAR(45) DEFAULT '',
    success BOOLEAN DEFAULT TRUE,
    severity VARCHAR(50) DEFAULT 'info',
    data_hash VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON memory.audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user ON memory.audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON memory.audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_severity ON memory.audit_log(severity);

-- =============================================================================
-- Schema: ledger
-- Purpose: Cryptographic blockchain ledger for integrity verification
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS ledger;

-- Blocks table - stores committed blocks
CREATE TABLE IF NOT EXISTS ledger.blocks (
    block_number BIGSERIAL PRIMARY KEY,
    previous_hash VARCHAR(64) NOT NULL,
    block_hash VARCHAR(64) UNIQUE NOT NULL,
    merkle_root VARCHAR(64) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    data_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_blocks_hash ON ledger.blocks(block_hash);
CREATE INDEX IF NOT EXISTS idx_blocks_timestamp ON ledger.blocks(timestamp DESC);

-- Entries table - stores individual ledger entries
CREATE TABLE IF NOT EXISTS ledger.entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    block_number BIGINT REFERENCES ledger.blocks(block_number),
    entry_type VARCHAR(100) NOT NULL,
    data_hash VARCHAR(64) NOT NULL,
    metadata JSONB DEFAULT '{}',
    signature VARCHAR(256),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entries_block ON ledger.entries(block_number);
CREATE INDEX IF NOT EXISTS idx_entries_type ON ledger.entries(entry_type);
CREATE INDEX IF NOT EXISTS idx_entries_hash ON ledger.entries(data_hash);
CREATE INDEX IF NOT EXISTS idx_entries_created ON ledger.entries(created_at DESC);

-- Proofs table - stores cryptographic proofs for verification
CREATE TABLE IF NOT EXISTS ledger.proofs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entry_id UUID REFERENCES ledger.entries(id),
    proof_type VARCHAR(50) NOT NULL,
    proof_data JSONB NOT NULL,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_proofs_entry ON ledger.proofs(entry_id);

-- Insert genesis block
INSERT INTO ledger.blocks (block_number, previous_hash, block_hash, merkle_root, data_count)
VALUES (0, '0000000000000000000000000000000000000000000000000000000000000000',
        'genesis_block_REDACTED_DB_PASSWORD',
        '0000000000000000000000000000000000000000000000000000000000000000', 0)
ON CONFLICT (block_number) DO NOTHING;

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
    type VARCHAR(50) NOT NULL,  -- mas, website, natureos, mindex, nlm, mycobrain
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
    method VARCHAR(10) NOT NULL,  -- GET, POST, PUT, DELETE, etc.
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
    type VARCHAR(50) NOT NULL,  -- orchestrator, worker, specialist, etc.
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
    type VARCHAR(50) NOT NULL,  -- api, worker, scheduler, etc.
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
    type VARCHAR(50) NOT NULL,  -- sporebase, mushroom1, nfc, sensor, etc.
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
    repository VARCHAR(100) NOT NULL,  -- mas, website, natureos, mindex, nlm, mycobrain
    file_path VARCHAR(512) NOT NULL,
    file_type VARCHAR(20) NOT NULL,  -- py, ts, tsx, cs, ino, etc.
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
    integration_type VARCHAR(50) NOT NULL,  -- api, message, database, etc.
    description TEXT,
    config JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_integrations_source ON registry.integrations(source_system);
CREATE INDEX IF NOT EXISTS idx_integrations_target ON registry.integrations(target_system);

-- =============================================================================
-- Schema: graph
-- Purpose: Knowledge graph for system relationships and semantic connections
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS graph;

-- Nodes table - entities in the knowledge graph
CREATE TABLE IF NOT EXISTS graph.nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_type VARCHAR(50) NOT NULL,  -- system, agent, api, service, device, concept, etc.
    name VARCHAR(255) NOT NULL,
    properties JSONB DEFAULT '{}',
    embedding FLOAT8[],  -- vector embedding for semantic search
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nodes_type ON graph.nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_nodes_name ON graph.nodes(name);

-- Edges table - relationships between nodes
CREATE TABLE IF NOT EXISTS graph.edges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES graph.nodes(id) ON DELETE CASCADE,
    target_id UUID REFERENCES graph.nodes(id) ON DELETE CASCADE,
    edge_type VARCHAR(50) NOT NULL,  -- depends_on, calls, contains, etc.
    properties JSONB DEFAULT '{}',
    weight FLOAT8 DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_edges_source ON graph.edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON graph.edges(target_id);
CREATE INDEX IF NOT EXISTS idx_edges_type ON graph.edges(edge_type);

-- Graph metadata table
CREATE TABLE IF NOT EXISTS graph.metadata (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- Views for common queries
-- =============================================================================

-- View: All active APIs with system info
CREATE OR REPLACE VIEW registry.v_active_apis AS
SELECT 
    a.id, a.path, a.method, a.description, a.tags,
    s.name as system_name, s.type as system_type, s.url as system_url
FROM registry.apis a
JOIN registry.systems s ON a.system_id = s.id
WHERE a.deprecated = FALSE AND s.status = 'active';

-- View: System health summary
CREATE OR REPLACE VIEW registry.v_system_health AS
SELECT 
    s.id, s.name, s.type, s.status,
    COUNT(DISTINCT sv.id) as service_count,
    COUNT(DISTINCT a.id) as api_count,
    COUNT(DISTINCT d.id) as device_count
FROM registry.systems s
LEFT JOIN registry.services sv ON sv.metadata->>'system' = s.name
LEFT JOIN registry.apis a ON a.system_id = s.id
LEFT JOIN registry.devices d ON d.metadata->>'system' = s.name
GROUP BY s.id;

-- View: Recent audit activity
CREATE OR REPLACE VIEW memory.v_recent_audit AS
SELECT * FROM memory.audit_log
ORDER BY timestamp DESC
LIMIT 1000;

-- View: Graph node connections
CREATE OR REPLACE VIEW graph.v_node_connections AS
SELECT 
    n.id, n.name, n.node_type,
    COUNT(DISTINCT e1.id) as outgoing_edges,
    COUNT(DISTINCT e2.id) as incoming_edges
FROM graph.nodes n
LEFT JOIN graph.edges e1 ON e1.source_id = n.id
LEFT JOIN graph.edges e2 ON e2.target_id = n.id
GROUP BY n.id;

-- =============================================================================
-- Functions
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to tables with updated_at
CREATE TRIGGER update_memory_entries_timestamp
    BEFORE UPDATE ON memory.entries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_registry_systems_timestamp
    BEFORE UPDATE ON registry.systems
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_registry_apis_timestamp
    BEFORE UPDATE ON registry.apis
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_registry_agents_timestamp
    BEFORE UPDATE ON registry.agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_registry_services_timestamp
    BEFORE UPDATE ON registry.services
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_registry_devices_timestamp
    BEFORE UPDATE ON registry.devices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_graph_nodes_timestamp
    BEFORE UPDATE ON graph.nodes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

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

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA memory TO mycosoft;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ledger TO mycosoft;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA registry TO mycosoft;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA graph TO mycosoft;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA memory TO mycosoft;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA ledger TO mycosoft;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA registry TO mycosoft;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA graph TO mycosoft;
