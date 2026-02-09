"""
Apply database migrations 013-016 to MINDEX PostgreSQL.
Created: February 5, 2026
"""
import paramiko
import os

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = os.getenv("SANDBOX_PASSWORD", "Mushroom1!Mushroom1!")

migrations = [
    ("013_unified_memory", """
CREATE SCHEMA IF NOT EXISTS memory;
CREATE TABLE IF NOT EXISTS memory.entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    layer VARCHAR(50) NOT NULL,
    content JSONB NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    accessed_at TIMESTAMPTZ DEFAULT NOW(),
    access_count INTEGER DEFAULT 0,
    importance FLOAT DEFAULT 0.5,
    status VARCHAR(50) DEFAULT 'active',
    tags TEXT[] DEFAULT '{}',
    hash VARCHAR(64)
);
CREATE INDEX IF NOT EXISTS idx_memory_layer ON memory.entries(layer);
CREATE INDEX IF NOT EXISTS idx_memory_importance ON memory.entries(importance DESC);
CREATE SCHEMA IF NOT EXISTS mem0;
CREATE TABLE IF NOT EXISTS mem0.memories (
    id VARCHAR(64) PRIMARY KEY,
    memory TEXT NOT NULL,
    user_id VARCHAR(255),
    agent_id VARCHAR(255),
    hash VARCHAR(64),
    metadata JSONB DEFAULT '{}'::jsonb,
    categories TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE SCHEMA IF NOT EXISTS mcp;
CREATE TABLE IF NOT EXISTS mcp.memories (
    id VARCHAR(64) PRIMARY KEY,
    content TEXT NOT NULL,
    category VARCHAR(50) DEFAULT 'general',
    importance FLOAT DEFAULT 0.5,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE SCHEMA IF NOT EXISTS cross_session;
CREATE TABLE IF NOT EXISTS cross_session.user_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    context_key VARCHAR(255) NOT NULL,
    context_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, context_key)
);
    """),
    ("014_voice_sessions", """
CREATE SCHEMA IF NOT EXISTS voice;
CREATE TABLE IF NOT EXISTS voice.sessions (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(255),
    speaker_profile VARCHAR(255),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    turns JSONB DEFAULT '[]'::jsonb,
    context JSONB DEFAULT '{}'::jsonb,
    summary TEXT,
    topics TEXT[] DEFAULT '{}',
    emotional_arc JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_voice_user ON voice.sessions(user_id);
    """),
    ("015_workflow_memory", """
CREATE SCHEMA IF NOT EXISTS workflow;
CREATE TABLE IF NOT EXISTS workflow.executions (
    id VARCHAR(64) PRIMARY KEY,
    workflow_id VARCHAR(255) NOT NULL,
    workflow_name VARCHAR(255),
    category VARCHAR(50),
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    duration_ms INTEGER,
    trigger VARCHAR(50) DEFAULT 'manual',
    input_data JSONB DEFAULT '{}'::jsonb,
    output_data JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    error_node VARCHAR(255),
    nodes_executed INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS workflow.patterns (
    id VARCHAR(64) PRIMARY KEY,
    workflow_id VARCHAR(255) NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,
    description TEXT,
    frequency INTEGER DEFAULT 0,
    last_seen TIMESTAMPTZ,
    conditions JSONB DEFAULT '{}'::jsonb,
    recommendations TEXT[] DEFAULT '{}',
    confidence FLOAT DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
    """),
    ("016_graph_persistence", """
CREATE SCHEMA IF NOT EXISTS graph;
CREATE TABLE IF NOT EXISTS graph.nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_type VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    properties JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(name, node_type)
);
CREATE TABLE IF NOT EXISTS graph.edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL,
    target_id UUID NOT NULL,
    edge_type VARCHAR(50) NOT NULL,
    properties JSONB DEFAULT '{}'::jsonb,
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_id, target_id, edge_type)
);
CREATE INDEX IF NOT EXISTS idx_graph_node_type ON graph.nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_graph_edge_source ON graph.edges(source_id);
CREATE INDEX IF NOT EXISTS idx_graph_edge_target ON graph.edges(target_id);
    """),
]

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(mindex_host, username=user, password=passwd, timeout=30)
    print(f"Connected to MINDEX VM at {mindex_host}")
    
    for name, sql in migrations:
        print(f"Applying migration: {name}")
        
        cmd = f'''docker exec -i mindex-postgres psql -U mycosoft -d mindex << 'EOSQL'
{sql}
EOSQL'''
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode()
        err = stderr.read().decode()
        
        if "ERROR" in err:
            print(f"  Errors: {err}")
        else:
            print(f"  Applied successfully")
    
    # Verify schemas exist
    cmd = '''docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('memory', 'mem0', 'mcp', 'cross_session', 'voice', 'workflow', 'graph') ORDER BY schema_name;"'''
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    print(f"\nSchemas created:\n{out}")
    
    ssh.close()
    print("Migration complete!")
    
except Exception as e:
    print(f"Error: {e}")
