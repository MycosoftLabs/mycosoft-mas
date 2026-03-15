#!/usr/bin/env python3
"""Force restart website container - Feb 6, 2026.
VM password from .credentials.local (VM_PASSWORD / VM_SSH_PASSWORD) or env."""
import os
import paramiko
import time

def _load_vm_password():
    creds_file = os.path.join(os.path.dirname(__file__), ".credentials.local")
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    if os.path.exists(creds_file):
        for line in open(creds_file).read().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                if k.strip() in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
                    password = v.strip()
                    break
    return password

_password = _load_vm_password()
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.187', username='mycosoft', password=_password, timeout=10)

# Force remove and recreate in background
cmd = '''
cd /home/mycosoft/mycosoft/mas
docker stop mycosoft-website 2>/dev/null || true
docker rm mycosoft-website 2>/dev/null || true
docker compose -f docker-compose.always-on.yml up -d mycosoft-website
'''

stdin, stdout, stderr = ssh.exec_command(f'''nohup bash -c '{cmd}' > /tmp/restart.log 2>&1 &
echo "Restart triggered"
''', timeout=5)
print(stdout.read().decode())

ssh.close()
print("Waiting 30 seconds for container to restart...")
time.sleep(30)

# Now test
ssh2 = paramiko.SSHClient()
ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh2.connect('192.168.0.187', username='mycosoft', password=_password, timeout=10)

stdin, stdout, stderr = ssh2.exec_command('curl -s http://localhost:3000/api/mycobrain/health', timeout=15)
stdout.channel.settimeout(15)
try:
    result = stdout.read().decode()
    print(f"Website health: {result}")
except Exception:
    print("Timeout reading result - container might still be starting")

ssh2.close()
