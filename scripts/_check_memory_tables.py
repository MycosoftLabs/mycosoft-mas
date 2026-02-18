#!/usr/bin/env python3
"""Check if memory schema and voice tables exist on MINDEX."""

import paramiko

VM_IP = "192.168.0.189"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"

# Connect to MINDEX VM
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)

print("Connected to MINDEX VM (192.168.0.189)")

# Check if memory schema and tables exist
print("\n=== CHECKING MEMORY SCHEMA AND TABLES ===")
cmd = "docker exec mindex-postgres psql -U mycosoft -d mindex -c \"SELECT schemaname, tablename FROM pg_tables WHERE schemaname = 'memory' ORDER BY tablename;\""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print(f"STDERR: {err}")

# Also check all schemas
print("\n=== ALL SCHEMAS ===")
cmd2 = "docker exec mindex-postgres psql -U mycosoft -d mindex -c \"SELECT schema_name FROM information_schema.schemata;\""
stdin, stdout, stderr = ssh.exec_command(cmd2)
print(stdout.read().decode())

ssh.close()
print("\n=== CHECK COMPLETE ===")
