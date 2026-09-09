"""One-shot 187 lock/status. Never prints secrets."""
from __future__ import annotations

import os
from pathlib import Path

import paramiko

CREDS = Path(__file__).resolve().parents[1] / ".credentials.local"
if not CREDS.exists():
    CREDS = Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.credentials.local")
for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
    if line and not line.startswith("#") and "=" in line:
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())

password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.0.187", username="mycosoft", password=password, timeout=30)


def run(command: str) -> str:
    _, stdout, stderr = client.exec_command(command, timeout=45)
    stdout.channel.recv_exit_status()
    return (stdout.read() + stderr.read()).decode("utf-8", "replace")


print("=== active-slot ===")
print(run("cat /opt/mycosoft/state/active-slot 2>/dev/null || echo missing"))
print("=== exclusive procs ===")
print(run("ps -ef | grep -E 'bg-cutover-exclusive|blue-green-deploy' | grep -v grep || true"))
print("=== docker slots ===")
print(run("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"))
print("=== lock files ===")
print(run("ls -l /opt/mycosoft/state /tmp/bg-cutover* 2>/dev/null | head -50"))
print("=== exclusive log tail ===")
print(run("tail -20 /tmp/bg-cutover-exclusive.log 2>/dev/null || echo none"))
client.close()
