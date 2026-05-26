#!/usr/bin/env python3
"""Verify production routes from sandbox VM (bypasses Cloudflare bot block)."""
import json
import os
from pathlib import Path

import paramiko

for fname in (Path(__file__).resolve().parents[1] / ".credentials.local",):
    if fname.exists():
        for line in fname.read_text(encoding="utf-8", errors="replace").splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip('"\'')

pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.0.187", username="mycosoft", password=pw, timeout=30)

checks = [
    ("GET", "http://localhost:3000/api/health", None),
    ("GET", "http://localhost:3000/natureos/earth-simulator", None),
    ("GET", "http://localhost:3000/api/crep/viewport-intel?north=34&south=33&east=-117&west=-118&zoom=9", None),
    (
        "POST",
        "http://localhost:3000/api/crep/viewport-ai-summary",
        '{"revision":"vm-verify-may26","context":{"revision":"vm-verify-may26","zoom":9,"center":{"lat":33.5,"lng":-117.5},"bounds":{"north":34,"south":33,"east":-117,"west":-118},"counts":{"events":1,"species":3},"infrastructure":["cell","power","military"]}}',
    ),
]

for method, url, body in checks:
    if method == "GET":
        cmd = f'curl -s -o /tmp/out.json -w "%{{http_code}}" "{url}"'
    else:
        cmd = (
            f'curl -s -o /tmp/out.json -w "%{{http_code}}" -X POST "{url}" '
            f'-H "Content-Type: application/json" -d \'{body}\''
        )
    _, stdout, _ = ssh.exec_command(cmd, timeout=60)
    code = stdout.read().decode().strip()
    _, stdout2, _ = ssh.exec_command("head -c 800 /tmp/out.json", timeout=15)
    snippet = stdout2.read().decode(errors="replace")
    print(f"\n=== {method} {url.split('localhost:3000')[-1]} -> HTTP {code} ===")
    print(snippet)
    if "viewport-intel" in url and code == "200":
        _, stdout3, _ = ssh.exec_command(
            "python3 -c \"import json;d=json.load(open('/tmp/out.json'));print('keys:',sorted(d.keys())[:20]);"
            "layers=d.get('layers') or d.get('infrastructure') or d.get('intel') or {}; "
            "print('sample:', str(layers)[:400] if layers else 'n/a')\"",
            timeout=20,
        )
        print(stdout3.read().decode(errors="replace"))

ssh.close()
