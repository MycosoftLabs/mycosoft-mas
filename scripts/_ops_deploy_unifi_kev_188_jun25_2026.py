#!/usr/bin/env python3
"""Deploy UniFi CISA KEV API changes to MAS VM 188 and restart orchestrator."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import paramiko

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_vm_credentials import load_vm_credentials

load_vm_credentials()

PASSWORD = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")
if not PASSWORD:
    print("Missing VM_PASSWORD")
    sys.exit(1)

MAS_ROOT = Path(__file__).resolve().parents[1]
REMOTE_BASE = "/home/mycosoft/mycosoft/mas/mycosoft_mas"
UPLOADS = [
    MAS_ROOT / "mycosoft_mas/core/routers/network_api.py",
    MAS_ROOT / "mycosoft_mas/services/network_diagnostics.py",
    MAS_ROOT / "mycosoft_mas/agents/network_monitor_agent.py",
]
SECURITY_SCRIPTS = [
    MAS_ROOT / "scripts/security/cve_2026_34908_check.py",
    MAS_ROOT / "scripts/security/probe_unifi_kev.py",
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.0.188", username="mycosoft", password=PASSWORD, timeout=20)

sftp = ssh.open_sftp()
for local in UPLOADS:
    rel = local.relative_to(MAS_ROOT / "mycosoft_mas").as_posix()
    remote = f"{REMOTE_BASE}/{rel}"
    sftp.put(str(local), remote)
    print(f"uploaded {rel}")

remote_scripts = "/home/mycosoft/mycosoft/mas/scripts/security"
ssh.exec_command(f"mkdir -p {remote_scripts}", timeout=10)
for local in SECURITY_SCRIPTS:
    remote = f"{remote_scripts}/{local.name}"
    sftp.put(str(local), remote)
    print(f"uploaded scripts/security/{local.name}")
sftp.close()

_, stdout, _ = ssh.exec_command(
    f"echo '{PASSWORD}' | sudo -S systemctl restart mas-orchestrator",
    timeout=90,
)
stdout.channel.recv_exit_status()
print("mas-orchestrator restarted")
time.sleep(12)

_, stdout, _ = ssh.exec_command(
    "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/api/network/kev",
    timeout=20,
)
kev_code = stdout.read().decode().strip()
print(f"/api/network/kev => HTTP {kev_code}")

_, stdout, _ = ssh.exec_command(
    "curl -s http://127.0.0.1:8001/health | head -c 200",
    timeout=20,
)
print("health:", stdout.read().decode().strip())
ssh.close()
sys.exit(0 if kev_code == "200" else 1)
