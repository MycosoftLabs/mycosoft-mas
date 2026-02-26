#!/usr/bin/env python3
"""One-shot: restart Docker, run website container on Sandbox 187."""
import os
import sys
import time
from pathlib import Path

# Load credentials
creds = Path(__file__).resolve().parent.parent / ".credentials.local"
if creds.exists():
    for line in creds.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")
user = os.environ.get("VM_SSH_USER", "mycosoft")
host = "192.168.0.187"

if not password:
    print("ERROR: No VM_PASSWORD in .credentials.local")
    sys.exit(1)

try:
    import paramiko
except ImportError:
    print("ERROR: paramiko not installed. Run: pip install paramiko")
    sys.exit(1)

def run(ssh_client, cmd: str, needs_sudo: bool = False) -> tuple[str, str, int]:
    """Run command via SSH, return (stdout, stderr, exit_code)."""
    cmd_run = f"sudo -S {cmd}" if needs_sudo else cmd
    stdin, stdout, stderr = ssh_client.exec_command(cmd_run, get_pty=True)
    if needs_sudo and password:
        stdin.write(password + "\n")
        stdin.flush()
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    return out, err, code

def run_simple(ssh_client, cmd: str) -> tuple[str, str, int]:
    stdin, stdout, stderr = ssh_client.exec_command(cmd)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    return out, err, code

print("Connecting to 192.168.0.187...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=30)

print("1. sudo systemctl restart docker")
out, err, code = run(client, "systemctl restart docker 2>&1", needs_sudo=True)
# Suppress password echo in output
out_s = (out or "").replace(password, "***")
err_s = (err or "").replace(password, "***")
print(out_s or err_s or "(no output)")
print(f"   exit: {code}\n")

if code != 0:
    print("   [Step 1 failed - Docker diagnostic] systemctl status docker:")
    o2, e2, c2 = run(client, "systemctl status docker.service 2>&1 | head -25", needs_sudo=True)
    print((o2 or e2 or "").replace(password, "***"))

print("2. sleep 20")
for _ in range(20):
    time.sleep(1)
    sys.stdout.write(".")
    sys.stdout.flush()
print()
print("   done\n")

print("3. docker images mycosoft-always-on-mycosoft-website")
out, err, code = run_simple(client, "docker images mycosoft-always-on-mycosoft-website --format '{{.Repository}}:{{.Tag}} {{.CreatedAt}}'")
print(out or err or "(no output)")
print(f"   exit: {code}\n")

print("4. docker rm -f mycosoft-website (if exists), then docker run")
run_simple(client, "docker rm -f mycosoft-website 2>/dev/null || true")
out2, err2, code2 = run_simple(client,
    "docker run -d --name mycosoft-website -p 3000:3000 "
    "-v /opt/mycosoft/media/website/assets:/app/public/assets:ro "
    "-e MAS_API_URL=http://192.168.0.188:8001 "
    "-e MYCOBRAIN_SERVICE_URL=http://192.168.0.187:8003 "
    "-e MYCOBRAIN_API_URL=http://192.168.0.187:8003 "
    "--restart unless-stopped mycosoft-always-on-mycosoft-website:latest"
)
print(out2 or err2 or "(no output)")
print(f"   exit: {code2}\n")

print("5. sleep 5")
time.sleep(5)
print("   done\n")

print("6. curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
out, err, code = run_simple(client, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
print(f"   HTTP: {out.strip() if out else 'N/A'}")
print(f"   exit: {code}\n")

client.close()
print("DONE. A later build-from-scratch is needed for latest code.")
