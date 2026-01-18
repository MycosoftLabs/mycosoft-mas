#!/usr/bin/env python3
"""Test static file access on VM."""

import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.187', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD')

print("=== Testing direct localhost access ===")
stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/_next/static/css/e205cd54c9e25594.css')
print(f"CSS file e205...: {stdout.read().decode()}")

stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/_next/static/css/5160586124011305.css')
print(f"CSS file 5160...: {stdout.read().decode()}")

# Check what chunks exist vs what the browser is requesting
print("\n=== Checking if requested chunks exist ===")
requested_chunks = [
    "4bd1b696-1f759126f2b25b4b.js",
    "webpack-5bc9086f4d81b5e6.js",
    "main-app-2e5788c1099c469f.js",
    "9440-129ee6d8fecfd296.js",
    "app/layout-8fc852b8474d7fed.js",
]

for chunk in requested_chunks:
    stdin, stdout, stderr = ssh.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" http://localhost:3000/_next/static/chunks/{chunk}')
    result = stdout.read().decode()
    status = "EXISTS" if result == "200" else "MISSING"
    print(f"  {chunk}: {status} ({result})")

ssh.close()
