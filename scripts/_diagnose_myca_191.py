#!/usr/bin/env python3
"""SSH to VM 191 and diagnose MYCA OS /channels."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
creds = {}
for f in [Path(__file__).parent.parent / ".credentials.local", Path.home() / ".mycosoft-credentials"]:
    if f.exists():
        for line in f.read_text().splitlines():
            if line.strip() and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                creds[k.strip()] = v.strip()
        break
pw = creds.get("VM_SSH_PASSWORD") or creds.get("VM_PASSWORD") or os.environ.get("VM_PASSWORD")
if not pw:
    print("No credentials")
    sys.exit(1)

import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.0.191", username="mycosoft", password=pw, timeout=15)


def run(cmd):
    _, o, e = ssh.exec_command(cmd, timeout=30)
    out = o.read().decode()
    err = e.read().decode()
    rc = o.channel.recv_exit_status()
    return out, err, rc


# Curl /channels
out, err, rc = run("curl -s -w ' HTTP_CODE:%{http_code}' http://127.0.0.1:8100/channels")
print("VM curl /channels:", repr(out), "rc:", rc)

# Curl /health
out2, _, _ = run("curl -s http://127.0.0.1:8100/health")
print("VM curl /health:", out2[:200])

# Check route registration in gateway
out3, _, _ = run("grep -n 'add_get\\|add_route' /home/mycosoft/repos/mycosoft-mas/mycosoft_mas/myca/os/gateway.py")
print("Route registrations:")
for line in (out3 or "").splitlines()[:25]:
    print(" ", line)

ssh.close()
