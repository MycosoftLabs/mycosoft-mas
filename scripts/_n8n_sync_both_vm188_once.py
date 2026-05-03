#!/usr/bin/env python3
"""SSH to MAS 188 and POST /api/workflows/sync-both (repo JSON -> local n8n)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parent.parent
for line in (ROOT / ".credentials.local").read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
if not pw:
    sys.exit("VM_PASSWORD missing")

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.0.188", username="mycosoft", password=pw, timeout=35)
_, stdout, stderr = client.exec_command(
    "curl -s -m 180 -X POST http://127.0.0.1:8001/api/workflows/sync-both "
    "-H 'Content-Type: application/json' -d '{}'",
    timeout=200,
)
print(stdout.read().decode("utf-8", errors="replace")[:8000])
err = stderr.read().decode("utf-8", errors="replace")
if err.strip():
    print(err, file=sys.stderr)
client.close()
