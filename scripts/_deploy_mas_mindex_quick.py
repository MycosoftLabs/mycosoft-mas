#!/usr/bin/env python3
"""Quick deploy: pull code and restart on MAS (188) and MINDEX (189)."""
import os
import paramiko
from pathlib import Path

creds_file = Path(__file__).parent.parent / ".credentials.local"
password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
if creds_file.exists():
    for line in creds_file.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            if key.strip() in ["VM_SSH_PASSWORD", "VM_PASSWORD"]:
                password = val.strip()
                break

def run(host: str, cmds: list[str]) -> bool:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        c.connect(host, username="mycosoft", password=password, timeout=15)
        for cmd in cmds:
            _, out, err = c.exec_command(cmd, timeout=120)
            code = out.channel.recv_exit_status()
            txt = (out.read() + err.read()).decode(errors="replace").strip()
            print(f"  [{host}] $ {cmd[:60]}... => {code}")
            if code != 0 and txt:
                print(f"    {txt[:200]}")
            elif code == 0 and "git" in cmd:
                for line in txt.split("\n")[:2]:
                    print(f"    {line}")
        return True
    except Exception as e:
        print(f"  [{host}] ERROR: {e}")
        return False
    finally:
        c.close()

print("Deploying MAS (188)...")
run("192.168.0.188", [
    "cd /home/mycosoft/mycosoft/mas && git fetch origin && git reset --hard origin/main && git log -1 --oneline",
    "sudo systemctl restart mas-orchestrator 2>/dev/null || (docker restart myca-orchestrator-new 2>/dev/null || true)",
])

print("\nDeploying MINDEX (189)...")
run("192.168.0.189", [
    "cd /home/mycosoft/mindex && git fetch origin && git reset --hard origin/main && git log -1 --oneline",
    "cd /home/mycosoft/mindex && docker compose restart mindex-api 2>/dev/null || true",
])

print("\nDone.")
