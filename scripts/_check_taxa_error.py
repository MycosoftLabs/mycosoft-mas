#!/usr/bin/env python3
"""Check taxa endpoint error"""
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
            print(out[-5000:] if len(out) > 5000 else out)
        if err.strip():
            print('STDERR:', err[-2000:] if len(err) > 2000 else err)
    return out, err

# Trigger the error
print('Triggering taxa query...')
run_cmd('curl -s "http://localhost:8000/api/mindex/taxa?q=amanita&limit=2"')

# Check the logs for error
print('\n\nChecking logs for error:')
run_cmd('docker logs mindex-api --tail 50 2>&1')

c.close()
print('\nDone!')
