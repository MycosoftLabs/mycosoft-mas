#!/usr/bin/env python3
"""Inspect MINDEX API on sandbox VM to locate telemetry-related endpoints."""

import json
import paramiko
import sys

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"


def run(ssh: paramiko.SSHClient, cmd: str) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return (out + ("\n" + err if err.strip() else "")).strip()


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)

    raw = run(ssh, "curl -s http://localhost:8000/openapi.json | head -c 400000 || true")
    ssh.close()

    try:
        doc = json.loads(raw)
    except Exception as e:
        print("[ERROR] Could not parse openapi.json:", e)
        print(raw[:1000])
        return

    paths = list((doc.get("paths") or {}).keys())
    telemetry_like = [p for p in paths if "telemetry" in p.lower() or "device" in p.lower()]
    print("[OK] total paths:", len(paths))
    print("[telemetry-like paths]")
    for p in telemetry_like[:200]:
        print(" -", p)


if __name__ == "__main__":
    main()

