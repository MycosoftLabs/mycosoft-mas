"""
Create registry.agents table in MINDEX PostgreSQL database.
Created: February 5, 2026
"""
import paramiko
import os

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = os.getenv("SANDBOX_PASSWORD", "Mushroom1!Mushroom1!")

# SQL to create the agents table
create_table_sql = """
-- Ensure registry schema exists
CREATE SCHEMA IF NOT EXISTS registry;

-- Create agents table
CREATE TABLE IF NOT EXISTS registry.agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(100) NOT NULL,
    description TEXT,
    module_path VARCHAR(500),
    class_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'offline',
    version VARCHAR(50) DEFAULT '1.0.0',
    capabilities JSONB DEFAULT '[]'::jsonb,
    dependencies JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    registered_at TIMESTAMPTZ DEFAULT NOW(),
    last_heartbeat TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on type for category queries
CREATE INDEX IF NOT EXISTS idx_agents_type ON registry.agents(type);

-- Create index on status for active agent queries
CREATE INDEX IF NOT EXISTS idx_agents_status ON registry.agents(status);

-- Create trigger to update updated_at
CREATE OR REPLACE FUNCTION registry.update_agents_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS agents_updated_at ON registry.agents;
CREATE TRIGGER agents_updated_at
    BEFORE UPDATE ON registry.agents
    FOR EACH ROW
    EXECUTE FUNCTION registry.update_agents_timestamp();
"""

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(mindex_host, username=user, password=passwd, timeout=30)
    print(f"Connected to MINDEX VM at {mindex_host}")
    
    # Execute create table SQL
    # Need to escape for shell
    escaped_sql = create_table_sql.replace('"', '\\"').replace("'", "'\\''")
    cmd = f"docker exec mindex-postgres psql -U mycosoft -d mindex -c \"{escaped_sql}\""
    
    # Actually, let's use a heredoc approach
    cmd = f'''docker exec -i mindex-postgres psql -U mycosoft -d mindex << 'EOSQL'
{create_table_sql}
EOSQL'''
    
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    
    print(f"Output: {out}")
    if err:
        print(f"Stderr: {err}")
    
    # Verify table was created
    verify_cmd = 'docker exec mindex-postgres psql -U mycosoft -d mindex -c "\\dt registry.*"'
    stdin, stdout, stderr = ssh.exec_command(verify_cmd)
    out = stdout.read().decode()
    print(f"\nRegistry tables:\n{out}")
    
    ssh.close()
    print("Table creation complete!")
    
except Exception as e:
    print(f"Error: {e}")
