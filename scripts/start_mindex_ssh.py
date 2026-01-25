#!/usr/bin/env python3
"""Start MINDEX containers via SSH"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import paramiko
except ImportError:
    print("Installing paramiko...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "paramiko", "-q"])
    import paramiko

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"

def run_ssh_cmd(cmd, timeout=120):
    """Run command via SSH"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30, banner_timeout=30)
        print(f"  [CMD] {cmd[:60]}...")
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        ssh.close()
        return out, err
    except Exception as e:
        print(f"  [ERR] {e}")
        return None, str(e)

print("=" * 60)
print("  MINDEX STARTUP VIA SSH")
print("=" * 60)

print("\n[1] Testing SSH connection...")
out, err = run_ssh_cmd("hostname && uptime")
if out:
    print(f"  Connected: {out.strip()}")
else:
    print(f"  Failed: {err}")
    sys.exit(1)

print("\n[2] Checking current containers...")
out, err = run_ssh_cmd("docker ps --format '{{.Names}} {{.Status}}' | head -10")
if out:
    print(f"{out}")

print("\n[3] Starting mindex-postgres first...")
out, err = run_ssh_cmd("""
cd /home/mycosoft/mindex-deploy && \
docker compose up -d mindex-postgres 2>&1
""")
print(out or err)

print("\n[4] Waiting 20s for postgres...")
import time
time.sleep(20)

print("\n[5] Starting mindex-api...")
out, err = run_ssh_cmd("""
cd /home/mycosoft/mindex-deploy && \
docker compose up -d mindex-api 2>&1
""")
print(out or err)

print("\n[6] Waiting 30s for api...")
time.sleep(30)

print("\n[7] Checking container status...")
out, err = run_ssh_cmd("docker ps --filter name=mindex --format '{{.Names}} {{.Status}}'")
print(out or err)

print("\n[8] Testing MINDEX API...")
out, err = run_ssh_cmd("curl -s http://localhost:8000/api/mindex/health 2>&1")
print(f"  Health: {out}")

out, err = run_ssh_cmd("curl -s http://localhost:8000/api/mindex/stats 2>&1 | head -c 300")
print(f"  Stats: {out}")

print("\n[9] MINDEX API Logs...")
out, err = run_ssh_cmd("docker logs mindex-api --tail 15 2>&1")
print(out or err)

print("\n" + "=" * 60)
print("  MINDEX STARTUP COMPLETE")
print("=" * 60)
