#!/usr/bin/env python3
"""Apply voice session store migration to MINDEX database - Feb 12, 2026"""

import os
import sys
from pathlib import Path

# Load credentials
creds_file = Path(__file__).parent.parent / ".credentials.local"
if creds_file.exists():
    for line in creds_file.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()

VM_HOST = "192.168.0.189"
VM_USER = os.environ.get("VM_SSH_USER", "mycosoft")
VM_PASSWORD = os.environ.get("VM_SSH_PASSWORD", os.environ.get("VM_PASSWORD"))

if not VM_PASSWORD:
    print("ERROR: No VM password found in .credentials.local or environment")
    sys.exit(1)

# Read migration SQL
# The MINDEX repo is at CODE/MINDEX/mindex, not CODE/MAS/MINDEX
code_root = Path(__file__).parent.parent.parent.parent  # CODE folder
migration_file = code_root / "MINDEX" / "mindex" / "migrations" / "0012_voice_session_store.sql"
if not migration_file.exists():
    print(f"ERROR: Migration file not found: {migration_file}")
    sys.exit(1)

sql_content = migration_file.read_text()
print(f"Loaded migration: {len(sql_content)} chars from {migration_file.name}")

# Connect and execute
import paramiko

print(f"Connecting to MINDEX VM ({VM_HOST})...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(VM_HOST, username=VM_USER, password=VM_PASSWORD, timeout=10)
    print("Connected!")
    
    # Write SQL to temp file on remote
    escaped_sql = sql_content.replace("'", "'\\''").replace("$", "\\$")
    
    # Write to temp file
    stdin, stdout, stderr = client.exec_command(f"cat > /tmp/voice_migration.sql << 'SQLDOC'\n{sql_content}\nSQLDOC")
    exit_code = stdout.channel.recv_exit_status()
    if exit_code != 0:
        print(f"Failed to write SQL file: {stderr.read().decode()}")
        sys.exit(1)
    print("SQL file written to /tmp/voice_migration.sql")
    
    # Execute migration
    cmd = "docker exec mindex-postgres psql -U mycosoft -d mindex -f /tmp/voice_migration.sql"
    stdin, stdout, stderr = client.exec_command(f"cat /tmp/voice_migration.sql | docker exec -i mindex-postgres psql -U mycosoft -d mindex")
    exit_code = stdout.channel.recv_exit_status()
    
    output = stdout.read().decode()
    errors = stderr.read().decode()
    
    print("\n--- Migration Output ---")
    print(output)
    if errors:
        print("--- Errors ---")
        print(errors)
    
    if exit_code == 0:
        print("\n✅ Voice session store migration applied successfully!")
    else:
        print(f"\n❌ Migration failed with exit code {exit_code}")
        sys.exit(1)
        
    # Verify tables exist
    print("\n--- Verifying tables ---")
    verify_cmd = "docker exec mindex-postgres psql -U mycosoft -d mindex -c \"SELECT tablename FROM pg_tables WHERE schemaname = 'memory' ORDER BY tablename;\""
    stdin, stdout, stderr = client.exec_command(verify_cmd)
    print(stdout.read().decode())
    
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
finally:
    client.close()
