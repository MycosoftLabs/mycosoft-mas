#!/usr/bin/env python3
"""
Create API Keys Schema in MINDEX PostgreSQL
Supports key management for Mycorrhizae, MINDEX, NatureOS, MycoBrain
"""

import paramiko
import sys
from datetime import datetime

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"
DB_CONTAINER = "mindex-postgres-data"
DB_USER = "mindex"
DB_NAME = "mindex"

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icons = {"INFO": "•", "OK": "✓", "WARN": "⚠", "ERROR": "✗", "HEAD": "▶", "SQL": "📄"}
    print(f"[{ts}] {icons.get(level, '•')} {msg}")

def run_ssh_cmd(ssh, cmd, timeout=120):
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        return out, err, stdout.channel.recv_exit_status()
    except Exception as e:
        return None, str(e), 1

def main():
    print("\n" + "="*70)
    print("     MINDEX API KEYS SCHEMA CREATION")
    print("     Creating tables for key management")
    print("="*70 + "\n")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        log("Connecting to Sandbox VM...", "HEAD")
        ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
        log("Connected to 192.168.0.187", "OK")
        
        # Check if postgres container is running
        log("Checking PostgreSQL container...", "HEAD")
        out, err, code = run_ssh_cmd(ssh, f"docker ps --filter name={DB_CONTAINER} --format '{{{{.Status}}}}'")
        if not out or "Up" not in out:
            log(f"PostgreSQL container not running: {out}", "ERROR")
            return 1
        log(f"PostgreSQL running: {out}", "OK")
        
        # Create the schema SQL
        schema_sql = """
-- ============================================
-- API KEYS MANAGEMENT SCHEMA
-- Mycorrhizae Protocol Key Management
-- ============================================

-- Drop existing tables if they exist (for clean reinstall)
DROP TABLE IF EXISTS api_key_usage CASCADE;
DROP TABLE IF EXISTS api_key_audit CASCADE;
DROP TABLE IF EXISTS api_keys CASCADE;

-- API Keys table
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash VARCHAR(64) NOT NULL UNIQUE,
    key_prefix VARCHAR(16) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    owner_id UUID,
    service VARCHAR(50) NOT NULL CHECK (service IN ('mycorrhizae', 'mindex', 'natureos', 'mycobrain', 'mas', 'admin')),
    scopes TEXT[] DEFAULT '{}',
    rate_limit_per_minute INT DEFAULT 60,
    rate_limit_per_day INT DEFAULT 10000,
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    usage_count BIGINT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    rotated_from UUID REFERENCES api_keys(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}'
);

-- API Key audit log
CREATE TABLE api_key_audit (
    id SERIAL PRIMARY KEY,
    key_id UUID REFERENCES api_keys(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL CHECK (action IN ('created', 'rotated', 'revoked', 'used', 'rate_limited', 'scope_changed', 'validated')),
    ip_address INET,
    user_agent TEXT,
    endpoint VARCHAR(255),
    response_code INT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Rate limiting tracking
CREATE TABLE api_key_usage (
    key_id UUID REFERENCES api_keys(id) ON DELETE CASCADE,
    window_start TIMESTAMPTZ NOT NULL,
    window_type VARCHAR(10) NOT NULL CHECK (window_type IN ('minute', 'hour', 'day')),
    request_count INT DEFAULT 1,
    PRIMARY KEY (key_id, window_start, window_type)
);

-- Indexes for performance
CREATE INDEX idx_api_keys_service ON api_keys(service);
CREATE INDEX idx_api_keys_owner ON api_keys(owner_id);
CREATE INDEX idx_api_keys_active ON api_keys(is_active) WHERE is_active = true;
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX idx_api_key_audit_key ON api_key_audit(key_id);
CREATE INDEX idx_api_key_audit_action ON api_key_audit(action);
CREATE INDEX idx_api_key_audit_created ON api_key_audit(created_at DESC);
CREATE INDEX idx_api_key_usage_window ON api_key_usage(window_start DESC);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_api_keys_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for updated_at
DROP TRIGGER IF EXISTS trigger_api_keys_updated_at ON api_keys;
CREATE TRIGGER trigger_api_keys_updated_at
    BEFORE UPDATE ON api_keys
    FOR EACH ROW
    EXECUTE FUNCTION update_api_keys_updated_at();

-- Insert default admin key (will be rotated on first use)
INSERT INTO api_keys (
    key_hash,
    key_prefix,
    name,
    description,
    service,
    scopes,
    rate_limit_per_minute,
    rate_limit_per_day
) VALUES (
    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    'myco_admin_def',
    'Default Admin Key',
    'Initial admin key - rotate immediately after setup',
    'admin',
    ARRAY['admin', 'read', 'write', 'keys:manage', 'keys:create', 'keys:revoke'],
    1000,
    100000
);

-- Log schema creation
INSERT INTO api_key_audit (key_id, action, metadata)
SELECT id, 'created', '{"note": "Schema initialization"}'::jsonb
FROM api_keys WHERE name = 'Default Admin Key';

-- Grant permissions
GRANT ALL ON api_keys TO mindex;
GRANT ALL ON api_key_audit TO mindex;
GRANT ALL ON api_key_usage TO mindex;
GRANT USAGE, SELECT ON SEQUENCE api_key_audit_id_seq TO mindex;
"""
        
        log("Creating API keys schema...", "SQL")
        
        # Write SQL to temp file and execute
        escaped_sql = schema_sql.replace("'", "'\\''")
        cmd = f"""docker exec {DB_CONTAINER} psql -U {DB_USER} -d {DB_NAME} -c '{escaped_sql}'"""
        
        out, err, code = run_ssh_cmd(ssh, cmd, timeout=60)
        
        if code != 0:
            log(f"Schema creation failed: {err}", "ERROR")
            # Try executing line by line
            log("Trying line-by-line execution...", "HEAD")
            
            statements = [
                "DROP TABLE IF EXISTS api_key_usage CASCADE",
                "DROP TABLE IF EXISTS api_key_audit CASCADE", 
                "DROP TABLE IF EXISTS api_keys CASCADE",
                """CREATE TABLE api_keys (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    key_hash VARCHAR(64) NOT NULL UNIQUE,
                    key_prefix VARCHAR(16) NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    owner_id UUID,
                    service VARCHAR(50) NOT NULL,
                    scopes TEXT[] DEFAULT ARRAY[]::TEXT[],
                    rate_limit_per_minute INT DEFAULT 60,
                    rate_limit_per_day INT DEFAULT 10000,
                    expires_at TIMESTAMPTZ,
                    last_used_at TIMESTAMPTZ,
                    usage_count BIGINT DEFAULT 0,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    rotated_from UUID,
                    metadata JSONB DEFAULT '{}'::jsonb
                )""",
                """CREATE TABLE api_key_audit (
                    id SERIAL PRIMARY KEY,
                    key_id UUID REFERENCES api_keys(id) ON DELETE CASCADE,
                    action VARCHAR(50) NOT NULL,
                    ip_address INET,
                    user_agent TEXT,
                    endpoint VARCHAR(255),
                    response_code INT,
                    metadata JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )""",
                """CREATE TABLE api_key_usage (
                    key_id UUID REFERENCES api_keys(id) ON DELETE CASCADE,
                    window_start TIMESTAMPTZ NOT NULL,
                    window_type VARCHAR(10) NOT NULL,
                    request_count INT DEFAULT 1,
                    PRIMARY KEY (key_id, window_start, window_type)
                )""",
                "CREATE INDEX IF NOT EXISTS idx_api_keys_service ON api_keys(service)",
                "CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active)",
                "CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix)",
                "CREATE INDEX IF NOT EXISTS idx_api_key_audit_key ON api_key_audit(key_id)",
                "CREATE INDEX IF NOT EXISTS idx_api_key_audit_created ON api_key_audit(created_at DESC)",
            ]
            
            for i, stmt in enumerate(statements):
                stmt_escaped = stmt.replace("'", "''").replace('"', '\\"')
                cmd = f'docker exec {DB_CONTAINER} psql -U {DB_USER} -d {DB_NAME} -c "{stmt_escaped}"'
                out, err, code = run_ssh_cmd(ssh, cmd)
                if code == 0:
                    log(f"  Statement {i+1}/{len(statements)}: OK", "OK")
                else:
                    log(f"  Statement {i+1}: {err[:50]}...", "WARN")
        else:
            log("Schema created successfully", "OK")
        
        # Verify tables exist
        log("Verifying tables...", "HEAD")
        verify_cmd = f"docker exec {DB_CONTAINER} psql -U {DB_USER} -d {DB_NAME} -c \"SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'api_key%'\""
        out, err, code = run_ssh_cmd(ssh, verify_cmd)
        if out:
            tables = [t.strip() for t in out.split('\n') if 'api_key' in t]
            log(f"Tables created: {', '.join(tables)}", "OK")
        
        # Check row count
        count_cmd = f"docker exec {DB_CONTAINER} psql -U {DB_USER} -d {DB_NAME} -t -c \"SELECT COUNT(*) FROM api_keys\""
        out, err, code = run_ssh_cmd(ssh, count_cmd)
        log(f"API keys in database: {out.strip()}", "OK")
        
        ssh.close()
        
        print("\n" + "="*70)
        print("     API KEYS SCHEMA CREATION COMPLETE")
        print("="*70)
        print("""
    Tables Created:
    ───────────────
    • api_keys        - Main key storage (hashed)
    • api_key_audit   - Audit log for all key operations
    • api_key_usage   - Rate limiting windows

    Default Admin Key:
    ──────────────────
    A default admin key has been created.
    Generate a new key using the Key Service API.
        """)
        
        return 0
        
    except Exception as e:
        log(f"Error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
