"""SSH to VM 188 and trigger n8n workflow sync-both via MAS API."""
import os
from pathlib import Path

creds = Path(__file__).resolve().parent.parent / ".credentials.local"
pw = ""
if creds.exists():
    for line in creds.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
                pw = v.strip()
                break
pw = pw or os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")

import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.0.188", username="mycosoft", password=pw, timeout=15)
stdin, stdout, stderr = client.exec_command(
    'curl -s -X POST "http://localhost:8001/api/workflows/sync-both" -H "Content-Type: application/json" -d "{}"'
)
out = stdout.read().decode()
err = stderr.read().decode()
client.close()
print(out or err or "no output")
print("Exit:", stdout.channel.recv_exit_status())
