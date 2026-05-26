#!/usr/bin/env python3
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

def run(host, user, cmds):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=pw, timeout=30)
    out = {}
    for name, cmd in cmds.items():
        _, stdout, stderr = ssh.exec_command(cmd, timeout=45)
        out[name] = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        if err.strip():
            out[name + "_err"] = err[:300]
    ssh.close()
    return out

# Sandbox: parse viewport-intel facilities
sb = run("192.168.0.187", "mycosoft", {
    "viewport_intel": 'curl -s "http://localhost:3000/api/crep/viewport-intel?north=34&south=33&east=-117&west=-118&zoom=9"',
})

data = json.loads(sb["viewport_intel"])
fac = data.get("facilities") or {}
print("viewport-intel top-level keys:", sorted(data.keys()))
print("facilities keys:", sorted(fac.keys()) if isinstance(fac, dict) else type(fac))
for k in ("military", "cell_towers", "power", "broadcast", "property", "wifi", "coverage"):
    if isinstance(fac, dict) and k in fac:
        v = fac[k]
        count = len(v) if isinstance(v, list) else "obj"
        print(f"  facilities.{k}: {count}")

# MINDEX fungal overlay route
mindex = run("192.168.0.189", "mycosoft", {
    "health": "curl -s http://localhost:8000/health",
    "fungal_cells": 'curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/mindex/fungal-overlays/cells?north=34&south=33&east=-117&west=-118"',
    "fungal_viewport": 'curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/mindex/fungal-overlays/viewport?north=34&south=33&east=-117&west=-118&zoom=9"',
    "civic_auth": 'curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/mindex/civic/viewport-intel?north=34&south=33&east=-117&west=-118&zoom=9"',
    "routers": "docker exec mindex-api ls /app/mindex_api/routers/ | grep -E 'civic|fungal'",
})
print("\nMINDEX health:", mindex["health"][:200])
print("MINDEX fungal-overlays/cells HTTP:", mindex.get("fungal_cells", ""))
print("MINDEX fungal-overlays/viewport HTTP:", mindex.get("fungal_viewport", ""))
print("MINDEX civic route HTTP:", mindex["civic_auth"])
print("MINDEX routers:", mindex["routers"].strip())

# MAS memory + sporebase/device routes
mas = run("192.168.0.188", "mycosoft", {
    "memory": "curl -s http://localhost:8001/api/memory/health",
    "devices": "curl -s http://localhost:8001/api/devices | python3 -c \"import sys,json;d=json.load(sys.stdin);print('count',d.get('count'));[print(x.get('device_role'),x.get('device_name')) for x in d.get('devices',[])]\"",
    "sporebase": 'curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/api/sporebase/health 2>/dev/null || echo missing',
})
print("\nMAS memory:", mas["memory"][:350])
print("MAS devices:\n", mas["devices"])
print("MAS sporebase health HTTP:", mas["sporebase"].strip())
