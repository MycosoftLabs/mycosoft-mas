#!/usr/bin/env python3
"""Check MINDEX Postgres configuration"""
import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('192.168.0.189', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD', timeout=30)

def run_cmd(cmd, print_output=True):
    stdin, stdout, stderr = c.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if print_output:
        if out.strip():
            print(out)
        if err.strip():
            print('STDERR:', err)
    return out, err

# Check postgres env vars
print('Postgres container env vars:')
run_cmd('docker exec mindex-postgres env | grep -E "POSTGRES|DB" | head -10')

# List postgres users
print('\nPostgres users:')
run_cmd('docker exec mindex-postgres psql -U postgres -c "\\du"')

# List databases
print('\nPostgres databases:')
run_cmd('docker exec mindex-postgres psql -U postgres -c "\\l"')

# Check if mindex database exists
print('\nMindex schema check:')
run_cmd('docker exec mindex-postgres psql -U postgres -d mindex -c "\\dt core.*" 2>&1 | head -20')

c.close()
print('\nDone!')
