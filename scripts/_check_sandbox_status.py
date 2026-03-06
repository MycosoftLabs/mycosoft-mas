#!/usr/bin/env python3
import os
from pathlib import Path
creds = Path(__file__).resolve().parent.parent / ".credentials.local"
if creds.exists():
    for line in creds.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

import paramiko
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.0.187", username="mycosoft", password=os.environ.get("VM_PASSWORD"), timeout=15)
_, o, _ = c.exec_command("docker ps --format '{{.Names}} {{.Status}}'; echo '---'; docker images mycosoft-always-on-mycosoft-website --format '{{.Tag}} {{.CreatedAt}}' 2>/dev/null | head -2")
print(o.read().decode())
c.close()
