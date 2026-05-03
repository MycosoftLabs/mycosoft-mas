#!/usr/bin/env python3
"""Import n8n/workflows/mindex_all_life_ingest.json into myca-n8n on VM 188."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parent.parent
WF = ROOT / "n8n/workflows/mindex_all_life_ingest.json"

for line in (ROOT / ".credentials.local").read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
if not pw or not WF.is_file():
    sys.exit("credentials or workflow file missing")

data = WF.read_bytes()
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.0.188", username="mycosoft", password=pw, timeout=35)
sftp = client.open_sftp()
remote = "/home/mycosoft/mindex_all_life_ingest.json"
with sftp.file(remote, "wb") as f:
    f.write(data)
sftp.close()

cmd = (
    f"docker cp {remote} myca-n8n:/tmp/mindex_all_life_ingest.json; "
    "docker exec myca-n8n n8n import:workflow --input=/tmp/mindex_all_life_ingest.json"
)
_, stdout, stderr = client.exec_command(cmd, timeout=120)
print(stdout.read().decode("utf-8", errors="replace"))
print(stderr.read().decode("utf-8", errors="replace"))
client.close()
