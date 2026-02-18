#!/usr/bin/env python3
"""Check voice schema tables on MINDEX."""

import paramiko

VM_IP = "192.168.0.189"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)

print("Connected to MINDEX VM (192.168.0.189)")

# Check voice schema tables
print("\n=== VOICE SCHEMA TABLES ===")
cmd = "docker exec mindex-postgres psql -U mycosoft -d mindex -c \"SELECT tablename FROM pg_tables WHERE schemaname = 'voice' ORDER BY tablename;\""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

# Check if voice_sessions exists anywhere
print("\n=== SEARCHING FOR voice_sessions ===")
cmd2 = "docker exec mindex-postgres psql -U mycosoft -d mindex -c \"SELECT schemaname, tablename FROM pg_tables WHERE tablename LIKE '%voice%' OR tablename LIKE '%session%';\""
stdin, stdout, stderr = ssh.exec_command(cmd2)
print(stdout.read().decode())

ssh.close()
