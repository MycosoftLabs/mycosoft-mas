#!/usr/bin/env python3
"""Audit all VMs (187,188,189,191), check code sync, services; deploy where needed; purge Cloudflare."""
import os
import sys
import time
import json
from pathlib import Path

creds = Path(__file__).resolve().parent.parent / ".credentials.local"
if creds.exists():
    for line in creds.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
if not pw:
    print("ERROR: VM_PASSWORD not set")
    sys.exit(1)

import paramiko

def run(ssh, cmd, timeout=60):
    _, o, e = ssh.exec_command(cmd, timeout=timeout)
    out = o.read().decode("utf-8", errors="replace")
    err = e.read().decode("utf-8", errors="replace")
    return o.channel.recv_exit_status(), out, err

def connect(ip):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(ip, username="mycosoft", password=pw, timeout=15)
    return c

results = {}

# --- SANDBOX 187 ---
print("\n=== SANDBOX (192.168.0.187) ===")
try:
    s = connect("192.168.0.187")
    ec, o, _ = run(s, "cd /opt/mycosoft/website 2>/dev/null && git fetch origin 2>/dev/null && git log -1 --oneline origin/main 2>/dev/null")
    results["187_git"] = o.strip() if ec == 0 else "N/A"
    ec2, o2, _ = run(s, "cd /opt/mycosoft/website 2>/dev/null && git log -1 --oneline 2>/dev/null")
    results["187_local"] = o2.strip() if ec2 == 0 else "N/A"
    results["187_behind"] = results["187_git"] != results["187_local"] if results["187_git"] != "N/A" else None
    ec3, o3, _ = run(s, "docker ps --format '{{.Names}} {{.Status}}' 2>/dev/null | grep -E 'mycosoft|website' || true")
    results["187_containers"] = o3.strip() or "none"
    ec4, o4, _ = run(s, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000 2>/dev/null")
    results["187_http"] = o4.strip() if o4.strip() else "?"
    s.close()
    print(f"  origin/main: {results['187_git']}")
    print(f"  local HEAD:  {results['187_local']}")
    print(f"  behind:      {results['187_behind']}")
    print(f"  containers:  {results['187_containers'][:80]}")
    print(f"  HTTP 3000:   {results['187_http']}")
except Exception as e:
    results["187_error"] = str(e)
    print(f"  ERROR: {e}")

# --- MAS 188 ---
print("\n=== MAS (192.168.0.188) ===")
try:
    s = connect("192.168.0.188")
    for p in ["/home/mycosoft/mycosoft/mas", "/opt/mycosoft/mas"]:
        ec, o, _ = run(s, f"cd {p} 2>/dev/null && git fetch origin 2>/dev/null && git log -1 --oneline origin/main 2>/dev/null")
        if ec == 0 and o.strip():
            results["188_path"] = p
            results["188_git"] = o.strip()
            ec2, o2, _ = run(s, f"cd {p} && git log -1 --oneline")
            results["188_local"] = o2.strip()
            results["188_behind"] = results["188_git"] != results["188_local"]
            break
    else:
        results["188_error"] = "MAS repo not found"
    ec3, o3, _ = run(s, "curl -s http://localhost:8001/health 2>/dev/null | head -c 200")
    results["188_health"] = "200" if "status" in o3 else o3[:50]
    ec4, o4, _ = run(s, "docker ps --format '{{.Names}} {{.Status}}' 2>/dev/null | grep -E 'orchestrator|mas|myca' || systemctl is-active mas-orchestrator 2>/dev/null || true")
    results["188_service"] = o4.strip() or "unknown"
    s.close()
    print(f"  path:   {results.get('188_path','?')}")
    print(f"  origin: {results.get('188_git','?')}")
    print(f"  local:  {results.get('188_local','?')}")
    print(f"  behind: {results.get('188_behind','?')}")
    print(f"  health: {results.get('188_health','?')[:60]}")
    print(f"  service: {results.get('188_service','?')}")
except Exception as e:
    results["188_error"] = str(e)
    print(f"  ERROR: {e}")

# --- MINDEX 189 ---
print("\n=== MINDEX (192.168.0.189) ===")
try:
    s = connect("192.168.0.189")
    for p in ["/home/mycosoft/mycosoft/mindex", "/opt/mycosoft/mindex"]:
        ec, o, _ = run(s, f"cd {p} 2>/dev/null && git fetch origin 2>/dev/null && git log -1 --oneline origin/main 2>/dev/null")
        if ec == 0 and o.strip():
            results["189_path"] = p
            results["189_git"] = o.strip()
            ec2, o2, _ = run(s, f"cd {p} && git log -1 --oneline")
            results["189_local"] = o2.strip()
            results["189_behind"] = results["189_git"] != results["189_local"]
            break
    else:
        results["189_error"] = "MINDEX repo not found"
    ec3, o3, _ = run(s, "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health 2>/dev/null")
    results["189_http"] = o3.strip()
    ec4, o4, _ = run(s, "docker ps --format '{{.Names}} {{.Status}}' 2>/dev/null | head -6")
    results["189_containers"] = o4.strip()[:200]
    s.close()
    print(f"  path:   {results.get('189_path','?')}")
    print(f"  origin: {results.get('189_git','?')}")
    print(f"  local:  {results.get('189_local','?')}")
    print(f"  behind: {results.get('189_behind','?')}")
    print(f"  HTTP 8000: {results.get('189_http','?')}")
    print(f"  containers: {results.get('189_containers','?')[:80]}")
except Exception as e:
    results["189_error"] = str(e)
    print(f"  ERROR: {e}")

# --- MYCA 191 ---
print("\n=== MYCA (192.168.0.191) ===")
try:
    s = connect("192.168.0.191")
    ec, o, _ = run(s, "curl -s -o /dev/null -w '%{http_code}' http://localhost:5679/healthz 2>/dev/null || curl -s -o /dev/null -w '%{http_code}' http://localhost:5678 2>/dev/null")
    results["191_n8n"] = o.strip() or "?"
    ec2, o2, _ = run(s, "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health 2>/dev/null")
    results["191_api"] = o2.strip() or "?"
    ec3, o3, _ = run(s, "systemctl is-active novnc 2>/dev/null; systemctl is-active xrdp 2>/dev/null")
    results["191_desktop"] = o3.strip()
    ec4, o4, _ = run(s, "docker ps --format '{{.Names}}' 2>/dev/null | head -5")
    results["191_containers"] = o4.strip()
    s.close()
    print(f"  n8n (5678/5679): {results.get('191_n8n','?')}")
    print(f"  API 8000:        {results.get('191_api','?')}")
    print(f"  desktop:         {results.get('191_desktop','?')}")
    print(f"  containers:      {results.get('191_containers','?')[:60]}")
except Exception as e:
    results["191_error"] = str(e)
    print(f"  ERROR: {e}")

# --- Summary & deploy decisions ---
print("\n" + "="*60)
needs_sandbox = results.get("187_behind") or results.get("187_http") != "200"
needs_mas = results.get("188_behind")
needs_mindex = results.get("189_behind")

deploy_actions = []
if needs_sandbox:
    deploy_actions.append("SANDBOX: pull, rebuild, restart (website)")
if needs_mas:
    deploy_actions.append("MAS: pull, rebuild/restart orchestrator")
if needs_mindex:
    deploy_actions.append("MINDEX: pull, rebuild mindex-api")

if deploy_actions:
    print("DEPLOY NEEDED:")
    for a in deploy_actions:
        print(f"  - {a}")
    out_path = Path(__file__).parent / "_vm_audit_results.json"
    with open(out_path, "w") as f:
        json.dump({"needs_sandbox": needs_sandbox, "needs_mas": needs_mas, "needs_mindex": needs_mindex, "results": results}, f, indent=2)
    print(f"\nResults: {out_path}")
else:
    print("ALL VMS UP TO PAR - no deploy needed.")

print("="*60)
