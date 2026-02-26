#!/usr/bin/env python3
"""Deploy MAS watchdog script to VM and add cron job."""

import os
import sys
import base64
from pathlib import Path

creds = Path(__file__).parent.parent / ".credentials.local"
if creds.exists():
    for line in creds.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

import paramiko

script = """#!/bin/bash
u="http://127.0.0.1:8001/health"
c="myca-orchestrator-new"
l="/home/mycosoft/mas_watchdog.log"
curl -sf -m 15 "$u" >/dev/null 2>&1 && exit 0
echo "$(date +%Y-%m-%dT%H:%M:%S) FAIL - restart" >> "$l"
docker restart "$c" >> "$l" 2>&1
"""

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.0.188", username="mycosoft", password=os.environ.get("VM_PASSWORD"), timeout=30)

def run(c):
    i, o, e = ssh.exec_command(c)
    return o.channel.recv_exit_status(), o.read().decode()

enc = base64.b64encode(script.encode()).decode()
run(f"echo {enc} | base64 -d > /home/mycosoft/mas_watchdog.sh")
run("chmod +x /home/mycosoft/mas_watchdog.sh")
print("Watchdog installed")

rc, out = run("crontab -l 2>/dev/null || true")
if "mas_watchdog" not in out:
    run('(crontab -l 2>/dev/null; echo "*/5 * * * * /home/mycosoft/mas_watchdog.sh") | crontab -')
    print("Cron added (every 5 min)")
else:
    print("Cron already exists")
ssh.close()
