#!/usr/bin/env python3
"""SCP Patch v2 files to MAS 188 and restart systemd orchestrator (merge-only env)."""
from __future__ import annotations

import os
import time
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
MAS_HOST = "192.168.0.188"
MAS_CODE = "/home/mycosoft/mycosoft/mas"

FILES = [
    "mycosoft_mas/compliance/evidence_emitter.py",
    "mycosoft_mas/core/routers/security_evidence_api.py",
    "mycosoft_mas/core/myca_main.py",
    "mycosoft_mas/core/routers/compliance_api.py",
    "mycosoft_mas/soc/repository.py",
]

MERGE_ENV_LINES = [
    "BGC_AUTOMATION_ENABLED=false",
]


def load_creds() -> None:
    creds = ROOT / ".credentials.local"
    for line in creds.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def connect() -> paramiko.SSHClient:
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(MAS_HOST, username="mycosoft", password=pw, timeout=20)
    return c


def run(c: paramiko.SSHClient, cmd: str, timeout: int = 120) -> tuple[int, str]:
    _, o, e = c.exec_command(cmd, timeout=timeout)
    out = o.read().decode(errors="replace")
    err = e.read().decode(errors="replace")
    return o.channel.recv_exit_status(), out + err


def upload_files(c: paramiko.SSHClient) -> None:
    sftp = c.open_sftp()
    run(c, f"mkdir -p {MAS_CODE}/mycosoft_mas/compliance")
    for rel in FILES:
        local = ROOT / rel
        remote = f"{MAS_CODE}/{rel.replace(chr(92), '/')}"
        remote_dir = str(Path(remote).parent).replace("\\", "/")
        run(c, f"mkdir -p {remote_dir}")
        print(f"upload {rel}")
        sftp.put(str(local), remote)
    sftp.close()


def merge_env(c: paramiko.SSHClient) -> None:
    env_path = f"{MAS_CODE}/.env"
    _, existing = run(c, f"test -f {env_path} && wc -l {env_path} || echo 0")
    print(f".env lines before merge: {existing.strip()}")
    for line in MERGE_ENV_LINES:
        key = line.split("=", 1)[0]
        run(
            c,
            f"grep -q '^{key}=' {env_path} 2>/dev/null && "
            f"sed -i 's|^{key}=.*|{line}|' {env_path} || echo '{line}' >> {env_path}",
        )
    code, out = run(c, f"grep -E '^(DATABASE_URL|MINDEX_DATABASE_URL|BGC_AUTOMATION)=' {env_path} | sed 's/=.*$/=***/'")
    print("env keys preserved (redacted):")
    print(out)


def restart_orchestrator(c: paramiko.SSHClient) -> None:
    code, out = run(c, "sudo -n systemctl restart mas-orchestrator 2>&1 || systemctl restart mas-orchestrator 2>&1")
    print("restart:", out.strip() or f"exit {code}")
    time.sleep(12)
    code, out = run(c, "systemctl is-active mas-orchestrator")
    print("is-active:", out.strip())


def probe() -> None:
    import json
    import urllib.request

    urls = {
        "screening_events": "http://192.168.0.188:8001/api/security/ps/screening-events",
        "compliance_score": "http://192.168.0.188:8001/api/compliance/score",
        "compliance_health": "http://192.168.0.188:8001/api/compliance/health",
    }
    for name, url in urls.items():
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                body = r.read(400).decode()
                print(f"{name}: HTTP {r.status} {body[:180]}")
        except Exception as ex:
            if hasattr(ex, "code"):
                print(f"{name}: HTTP {ex.code}")
            else:
                print(f"{name}: error {ex}")


def main() -> None:
    load_creds()
    c = connect()
    try:
        upload_files(c)
        merge_env(c)
        restart_orchestrator(c)
    finally:
        c.close()
    print("\n--- probes ---")
    probe()


if __name__ == "__main__":
    main()
