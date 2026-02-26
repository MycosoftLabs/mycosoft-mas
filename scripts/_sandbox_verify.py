#!/usr/bin/env python3
import os, sys
from pathlib import Path
import paramiko

REPO = Path(__file__).resolve().parent.parent
for line in (REPO / ".credentials.local").read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()
p = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.168.0.187", username="mycosoft", password=p, timeout=30)
_, o, e = c.exec_command("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000", 15)
http = (o.read() + e.read()).decode().strip()
_, o, e = c.exec_command("docker ps --filter name=mycosoft-website")
ps = (o.read() + e.read()).decode()
c.close()
print("HTTP status:", http)
print("Container:\n", ps)
# Cloudflare purge
sys.path.insert(0, str(REPO.parent.parent / "WEBSITE" / "website"))
try:
    from _cloudflare_cache import purge_everything
    purge_everything()
except Exception as ex:
    print("Purge error:", ex)
sys.exit(0 if http == "200" else 1)
