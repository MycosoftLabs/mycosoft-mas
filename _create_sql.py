import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
mindex_user = "mycosoft"
mindex_pass = "Mushroom1!Mushroom1!"

print("Connecting to MINDEX VM...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=mindex_user, password=mindex_pass, timeout=30)
print("Connected!")

# Create init-postgres.sql
print("\n=== Creating init-postgres.sql ===")
init_sql = '''
-- MINDEX PostgreSQL Schema Initialization
-- February 4, 2026

-- Create schemas
CREATE SCHEMA IF NOT EXISTS memory;
CREATE SCHEMA IF NOT EXISTS ledger;
CREATE SCHEMA IF NOT EXISTS registry;
CREATE SCHEMA IF NOT EXISTS graph;

-- Memory schema tables
CREATE TABLE IF NOT EXISTS memory.entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope VARCHAR(50) NOT NULL,
    namespace VARCHAR(255) NOT NULL,
    key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ,
    data_hash VARCHAR(64),
    UNIQUE(scope, namespace, key)
);

CREATE TABLE IF NOT EXISTS memory.audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_type VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    scope VARCHAR(50),
    namespace VARCHAR(255),
    key VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    data_hash VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Ledger schema tables
CREATE TABLE IF NOT EXISTS ledger.blocks (
    block_number SERIAL PRIMARY KEY,
    previous_hash VARCHAR(64) NOT NULL,
    block_hash VARCHAR(64) NOT NULL UNIQUE,
    merkle_root VARCHAR(64) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    entry_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ledger.entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    block_number INTEGER REFERENCES ledger.blocks(block_number),
    entry_type VARCHAR(50) NOT NULL,
    data_hash VARCHAR(64) NOT NULL,
    signature VARCHAR(128),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Insert genesis block
INSERT INTO ledger.blocks (block_number, previous_hash, block_hash, merkle_root, entry_count)
VALUES (0, '0000000000000000000000000000000000000000000000000000000000000000',
        'genesis_mindex_2026_02_04',
        '0000000000000000000000000000000000000000000000000000000000000000', 0)
ON CONFLICT DO NOTHING;

-- Registry schema tables
CREATE TABLE IF NOT EXISTS registry.systems (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    type VARCHAR(50) NOT NULL,
    url VARCHAR(500),
    description TEXT,
    status VARCHAR(20) DEFAULT 'active',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS registry.apis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    system_id UUID REFERENCES registry.systems(id),
    path VARCHAR(500) NOT NULL,
    method VARCHAR(10) NOT NULL,
    description TEXT,
    parameters JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS registry.devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    firmware_version VARCHAR(50),
    status VARCHAR(20) DEFAULT 'offline',
    last_seen TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Graph schema tables
CREATE TABLE IF NOT EXISTS graph.nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    node_type VARCHAR(50) NOT NULL,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS graph.edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES graph.nodes(id) ON DELETE CASCADE,
    target_id UUID REFERENCES graph.nodes(id) ON DELETE CASCADE,
    edge_type VARCHAR(50) NOT NULL,
    properties JSONB DEFAULT '{}',
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_memory_scope_ns ON memory.entries(scope, namespace);
CREATE INDEX IF NOT EXISTS idx_memory_expires ON memory.entries(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ledger_entries_block ON ledger.entries(block_number);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_type ON graph.nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_graph_edges_source ON graph.edges(source_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_target ON graph.edges(target_id);

-- Insert core systems
INSERT INTO registry.systems (name, type, url, description)
VALUES 
    ('MAS', 'orchestrator', 'http://192.168.0.188:8001', 'Multi-Agent System Orchestrator'),
    ('Website', 'frontend', 'http://192.168.0.187:3000', 'Mycosoft Dashboard and Website'),
    ('MINDEX', 'database', 'http://192.168.0.189:8000', 'Memory Index and Knowledge Graph'),
    ('NatureOS', 'platform', 'http://192.168.0.188:5000', 'Nature Operating System'),
    ('NLM', 'ml', 'http://192.168.0.188:8200', 'Nature Learning Models'),
    ('MycoBrain', 'iot', 'http://192.168.0.188:8080', 'IoT Device Management')
ON CONFLICT DO NOTHING;

SELECT 'MINDEX database initialized successfully!' as status;
'''

# Write init SQL
cmd = f'''cat > /opt/mycosoft/mindex/init-postgres.sql << 'SQLEOF'
{init_sql}
SQLEOF
echo "init-postgres.sql created"
ls -la /opt/mycosoft/mindex/
'''
stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(3)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
