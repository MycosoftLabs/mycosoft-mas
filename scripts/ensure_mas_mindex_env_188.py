#!/usr/bin/env python3
"""
Sync MINDEX_INTERNAL_TOKEN from MINDEX VM (189) into MAS VM (188) .env and restart mas-orchestrator.

Uses .credentials.local (VM_PASSWORD, optional MINDEX_INTERNAL_TOKEN fallback).
Never prints full tokens. Safe to run idempotently.

Usage (from MAS repo root):
  python scripts/ensure_mas_mindex_env_188.py
  python scripts/ensure_mas_mindex_env_188.py --verify-only
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import paramiko

REPO_ROOT = Path(__file__).resolve().parent.parent
CREDS = REPO_ROOT / ".credentials.local"
MAS_HOST = os.environ.get("MAS_VM_IP", "192.168.0.188")
MINDEX_HOST = os.environ.get("MINDEX_VM_HOST", "192.168.0.189")
ENV_PATH = "/home/mycosoft/mycosoft/mas/.env"


def load_credentials() -> None:
    if not CREDS.exists():
        print(f"Missing {CREDS}", file=sys.stderr)
        sys.exit(1)
    for line in CREDS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def connect(host: str) -> paramiko.SSHClient:
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")
    if not password:
        print("VM_PASSWORD not set", file=sys.stderr)
        sys.exit(1)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=os.environ.get("VM_SSH_USER", "mycosoft"), password=password, timeout=30)
    return ssh


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 90) -> tuple[int, str]:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    code = stdout.channel.recv_exit_status()
    return code, (stdout.read() + stderr.read()).decode(errors="replace").strip()


def fetch_mindex_token_from_189(ssh: paramiko.SSHClient) -> str:
    py = r"""
import json, subprocess, sys
out = subprocess.check_output(
    ["docker", "inspect", "mindex-api", "--format", "{{json .Config.Env}}"],
    text=True,
)
for e in json.loads(out):
    if e.startswith("MINDEX_INTERNAL_TOKENS="):
        print(e.split("=", 1)[1].split(",")[0].strip())
        sys.exit(0)
    if e.startswith("MINDEX_INTERNAL_TOKEN="):
        print(e.split("=", 1)[1].strip())
        sys.exit(0)
sys.exit(2)
"""
    code, out = run(ssh, "python3 -c " + json.dumps(py))
    if code == 0 and out:
        return out.splitlines()[-1].strip()
    fallback = os.environ.get("MINDEX_INTERNAL_TOKEN", "").strip()
    if fallback:
        return fallback
    raise RuntimeError(f"Could not read MINDEX token from 189 (exit {code})")


def patch_env(content: str, key: str, value: str) -> str:
    pat = re.compile(rf"^{re.escape(key)}=.*$", re.M)
    if pat.search(content):
        return pat.sub(f"{key}={value}", content)
    if content and not content.endswith("\n"):
        content += "\n"
    return content + f"{key}={value}\n"


def restart_mas_orchestrator(ssh: paramiko.SSHClient, sudo_password: str) -> None:
    remote_py = "/tmp/_ensure_mas_restart.py"
    script = (
        "import subprocess, sys\n"
        "pw = sys.stdin.read().strip()\n"
        "subprocess.run(\n"
        '    ["sudo", "-S", "systemctl", "restart", "mas-orchestrator"],\n'
        '    input=pw + "\\n", text=True, capture_output=True, timeout=90,\n'
        ")\n"
    )
    sftp = ssh.open_sftp()
    with sftp.file(remote_py, "w") as f:
        f.write(script)
    sftp.close()
    _, stdout, stderr = ssh.exec_command(f"python3 {remote_py}", timeout=120)
    stdout.channel.send(sudo_password + "\n")
    stdout.channel.shutdown_write()
    stdout.channel.recv_exit_status()
    run(ssh, f"rm -f {remote_py}")


def verify_endpoints(ssh: paramiko.SSHClient, token: str) -> bool:
    sftp = ssh.open_sftp()
    with sftp.file("/tmp/mindex_verify_hdr", "w") as f:
        f.write(f"X-Internal-Token: {token}\n")
    sftp.close()
    checks = [
        ("health_sha", "curl -sf http://127.0.0.1:8001/health | python3 -c \"import sys,json; print(json.load(sys.stdin).get('git_sha','')[:12])\""),
        ("lib_health", "curl -s -o /dev/null -w '%{http_code}' -H @/tmp/mindex_verify_hdr http://127.0.0.1:8001/api/mas/mindex/library/health"),
        ("blobs", "curl -s -o /dev/null -w '%{http_code}' -H @/tmp/mindex_verify_hdr 'http://127.0.0.1:8001/api/mas/mindex/library/blobs?limit=3'"),
        ("sine", "curl -s -o /dev/null -w '%{http_code}' -H @/tmp/mindex_verify_hdr 'http://127.0.0.1:8001/api/mas/mindex/library/sine/human-tags?limit=5'"),
    ]
    ok = True
    for name, cmd in checks:
        _, out = run(ssh, cmd)
        print(f"  {name}: {out}")
        if name != "health_sha" and out != "200":
            ok = False
    run(ssh, "rm -f /tmp/mindex_verify_hdr")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    load_credentials()

    ssh189 = connect(MINDEX_HOST)
    try:
        token = fetch_mindex_token_from_189(ssh189)
    finally:
        ssh189.close()
    print(f"MINDEX token: len={len(token)} prefix={token[:8]}...")

    ssh188 = connect(MAS_HOST)
    try:
        if args.verify_only:
            return 0 if verify_endpoints(ssh188, token) else 1

        _, cur = run(ssh188, f"cat {ENV_PATH} 2>/dev/null || echo ''")
        mindex_url = os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8000")
        for key, val in [
            ("MINDEX_API_URL", mindex_url),
            ("MINDEX_INTERNAL_TOKEN", token),
            ("MAS_API_URL", f"http://{MAS_HOST}:8001"),
            ("NLM_INFERENCE_URL", f"http://{MAS_HOST}:8001"),
        ]:
            cur = patch_env(cur, key, val)

        local = Path(__file__).parent / ".ensure_mas_env.tmp"
        local.write_text(cur, encoding="utf-8")
        sftp = ssh188.open_sftp()
        sftp.put(str(local), f"{ENV_PATH}.new")
        sftp.close()
        local.unlink(missing_ok=True)
        run(ssh188, f"mv {ENV_PATH}.new {ENV_PATH} && chmod 600 {ENV_PATH}")
        print(f"Updated {ENV_PATH}")

        sudo_pw = os.environ["VM_PASSWORD"]
        restart_mas_orchestrator(ssh188, sudo_pw)
        time.sleep(10)
        _, active = run(ssh188, "systemctl is-active mas-orchestrator")
        print(f"mas-orchestrator: {active}")
        if active != "active":
            return 1
        print("Verification:")
        return 0 if verify_endpoints(ssh188, token) else 1
    finally:
        ssh188.close()


if __name__ == "__main__":
    raise SystemExit(main())
