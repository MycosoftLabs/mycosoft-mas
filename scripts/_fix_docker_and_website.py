#!/usr/bin/env python3
"""Fix zombie dockerd, restart Docker, run website container on Sandbox 187."""
import os
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

creds = Path(__file__).resolve().parent.parent / ".credentials.local"
if creds.exists():
    for line in creds.read_text().splitlines():
        if line and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")
user = os.environ.get("VM_SSH_USER", "mycosoft")
host = "192.168.0.187"

if not password:
    print("ERROR: No VM_PASSWORD in .credentials.local")
    sys.exit(1)

import paramiko

def run_sudo(client, cmd):
    stdin, stdout, stderr = client.exec_command("sudo -S sh -c " + repr(cmd), get_pty=True)
    stdin.write(password + "\n")
    stdin.flush()
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    return (out + err).replace(password, "***"), code

def run(client, cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    return out + err, code

print("Connecting to 192.168.0.187...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=30)

print("0. Stop docker, kill all dockerd, remove stale pid")
out, code = run_sudo(client,
    "systemctl stop docker docker.socket 2>/dev/null; "
    "sleep 2; "
    "for pid in $(pgrep -x dockerd); do kill -9 $pid 2>/dev/null; done; "
    "pkill -9 -f dockerd 2>/dev/null; "
    "sleep 2; "
    "rm -f /var/run/docker.pid; "
    "echo done")
print(out or "OK")
print(f"   exit: {code}\n")

print("1. sudo systemctl restart docker")
out, code = run_sudo(client, "systemctl restart docker 2>&1")
print(out or "(no output)")
print(f"   exit: {code}\n")

if code != 0:
    print("   [Diagnostic] systemctl status docker:")
    out2, _ = run_sudo(client, "systemctl status docker.service 2>&1 | head -25")
    print(out2)
    client.close()
    sys.exit(1)

print("2. sleep 20")
time.sleep(20)
print("   done\n")

print("3. docker images mycosoft-always-on-mycosoft-website")
out, code = run(client, "docker images mycosoft-always-on-mycosoft-website --format '{{.Repository}}:{{.Tag}} {{.CreatedAt}}'")
print(out or "(no output)")
print(f"   exit: {code}\n")

print("4. docker rm -f mycosoft-website (if exists), then docker run")
run(client, "docker rm -f mycosoft-website 2>/dev/null || true")
out2, code2 = run(client,
    "docker run -d --name mycosoft-website -p 3000:3000 "
    "-v /opt/mycosoft/media/website/assets:/app/public/assets:ro "
    "-e MAS_API_URL=http://192.168.0.188:8001 "
    "-e MYCOBRAIN_SERVICE_URL=http://192.168.0.187:8003 "
    "-e MYCOBRAIN_API_URL=http://192.168.0.187:8003 "
    "--restart unless-stopped mycosoft-always-on-mycosoft-website:latest"
)
print(out2 or "(no output)")
print(f"   exit: {code2}\n")

print("5. sleep 5")
time.sleep(5)
print("   done\n")

print("6. curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
out, code = run(client, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
print(f"   HTTP: {out.strip() if out else 'N/A'}")
print(f"   exit: {code}\n")

client.close()
print("DONE. A later build-from-scratch is needed for latest code.")
