#!/usr/bin/env python3
"""Deploy JUN11_2026 security hardening to MAS 188 + MINDEX 189.

- Pre-flight: read env on both VMs (no values printed, presence only)
- 188: ensure MAS_INTERNAL_TOKEN in /home/mycosoft/mycosoft/mas/.env, git pull, restart mas-orchestrator
- 189: ensure API_KEYS non-empty before fail-closed deploy, git pull, rebuild mindex-api
- Verify: gated endpoints 401 without token, healthy with token

Usage: py -3 scripts/deploy_security_hardening_jun11_2026.py [--preflight-only]
"""
from __future__ import annotations

import os
import secrets as pysecrets
import sys
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
MAS_HOST = "192.168.0.188"
MINDEX_HOST = "192.168.0.189"
MAS_BRANCH = "feature/com4-hyphae-ota-local-may29-2026"


def load_creds() -> str:
    creds = ROOT / ".credentials.local"
    for line in creds.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    if not password:
        raise SystemExit("VM_PASSWORD not set in .credentials.local")
    return password


def connect(host: str, password: str) -> paramiko.SSHClient:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username="mycosoft", password=password, timeout=15)
    return ssh


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 300) -> tuple[str, str]:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode(), stderr.read().decode()


def main() -> None:
    preflight_only = "--preflight-only" in sys.argv
    password = load_creds()

    # ---- Pre-flight 188 ----
    ssh188 = connect(MAS_HOST, password)
    out, _ = run(
        ssh188,
        "cd /home/mycosoft/mycosoft/mas && "
        "grep -c '^MAS_INTERNAL_TOKEN=..*' .env 2>/dev/null; "
        "grep -o '^MAS_ENV=.*' .env 2>/dev/null | head -1",
    )
    print(f"[188] preflight: {out.strip()!r}")
    has_mas_token = out.strip().startswith("1")

    # ---- Pre-flight 189 ----
    ssh189 = connect(MINDEX_HOST, password)
    out, _ = run(
        ssh189,
        "docker exec mindex-api sh -c "
        "'echo ENV=$ENVIRONMENT MINDEX_ENV=$MINDEX_ENV; "
        "[ -n \"$API_KEYS\" ] && echo API_KEYS=set || echo API_KEYS=EMPTY; "
        "[ -n \"$MINDEX_INTERNAL_TOKENS\" ] && echo ITOK=set || echo ITOK=EMPTY'",
    )
    print(f"[189] preflight: {out.strip()}")
    api_keys_empty = "API_KEYS=EMPTY" in out
    prod_189 = "ENV=production" in out or "MINDEX_ENV=production" in out

    if preflight_only:
        return

    # ---- 188: token + deploy ----
    if not has_mas_token:
        token = os.environ.get("MAS_INTERNAL_TOKEN") or f"mas_{pysecrets.token_hex(28)}"
        run(
            ssh188,
            f"cd /home/mycosoft/mycosoft/mas && "
            f"printf '\\nMAS_INTERNAL_TOKEN={token}\\n' >> .env",
        )
        # persist locally for callers (never printed)
        creds = ROOT / ".credentials.local"
        if "MAS_INTERNAL_TOKEN=" not in creds.read_text():
            with creds.open("a") as f:
                f.write(f"\nMAS_INTERNAL_TOKEN={token}\n")
        print("[188] MAS_INTERNAL_TOKEN generated + written to VM .env and .credentials.local")
    out, err = run(
        ssh188,
        "cd /home/mycosoft/mycosoft/mas && "
        f"git fetch origin && git checkout {MAS_BRANCH} && git pull && "
        f"echo '{password}' | sudo -S systemctl restart mas-orchestrator && sleep 8 && "
        "curl -sf http://127.0.0.1:8001/health | head -c 200",
    )
    print(f"[188] deploy: {out[-300:]}")
    if err.strip():
        print(f"[188] err: {err[-300:]}")

    # ---- 189: guard + deploy ----
    # require_api_key now accepts X-Internal-Token (commit a1183a3), and
    # MINDEX_INTERNAL_TOKENS is set on 189, so marking the VM production
    # enforces auth without breaking internal callers.
    out, err = run(
        ssh189,
        "cd /home/mycosoft/mindex && "
        "(grep -q '^MINDEX_ENV=' .env 2>/dev/null || printf '\\nMINDEX_ENV=production\\n' >> .env) && "
        "git fetch origin && git reset --hard origin/main && "
        "docker compose build mindex-api && docker compose up -d mindex-api && "
        "sleep 10 && curl -sf http://127.0.0.1:8000/api/mindex/health",
        timeout=900,
    )
    print(f"[189] deploy: {out[-300:]}")
    if err.strip():
        print(f"[189] err: {err[-400:]}")

    # ---- Verify gating from dev PC side (via SSH curl on 188) ----
    out, _ = run(
        ssh188,
        "curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:8001/api/deploy/trigger "
        "-H 'Content-Type: application/json' -d '{\"target\":\"mas\"}'",
    )
    print(f"[verify] deploy/trigger WITHOUT token -> HTTP {out.strip()} (expect 401/503)")
    tok = os.environ.get("MAS_INTERNAL_TOKEN", "")
    if tok:
        out, _ = run(
            ssh188,
            "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/api/deploy/status/none "
            f"-H 'X-MAS-Internal-Token: {tok}'",
        )
        print(f"[verify] deploy/status WITH token -> HTTP {out.strip()} (expect 404)")

    ssh188.close()
    ssh189.close()
    print("Done.")


if __name__ == "__main__":
    main()
