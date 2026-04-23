#!/usr/bin/env python3
"""Run Morgan's 8230 checklist on Voice 241 and Earth-2 249 (Windows + WSL). Uses same SSH as ensure_legion_crep_tile_stubs_8230.py."""
from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

import paramiko

REPO = Path(__file__).resolve().parent.parent

HOSTS: tuple[tuple[str, str], ...] = (
    ("192.168.0.241", "241"),
    ("192.168.0.249", "249"),
)


def _load_creds() -> str:
    cfile = REPO / ".credentials.local"
    if cfile.exists():
        for line in cfile.read_text(encoding="utf-8", errors="replace").splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))
    return os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""


def _user_for_host(host: str) -> str:
    if "241" in host:
        return (os.environ.get("LEGION241_SSH_USER") or "owner1").strip()
    if "249" in host:
        return (os.environ.get("LEGION249_SSH_USER") or "owner2").strip()
    return "owner1"


def _ssh_key_path() -> Path | None:
    keyp = (os.environ.get("LEGION_SSH_KEY") or os.path.expanduser("~/.ssh/id_ed25519")).strip()
    p = Path(keyp)
    return p if p.is_file() else None


def _ps_diag(host_ip: str) -> str:
    return rf"""
$ErrorActionPreference = "Continue"
$ip = "{host_ip}"
Write-Host "=== Get-Process python/uvicorn ==="
Get-Process -ErrorAction SilentlyContinue | Where-Object {{ $_.ProcessName -match "python|uvicorn" }} | Select-Object Id,ProcessName,StartTime
Write-Host "`n=== netstat :8230 ==="
netstat -ano | findstr :8230
Write-Host "`n=== portproxy (v4) ==="
netsh interface portproxy show all
Write-Host "`n=== IWR 127.0.0.1:8230/health ==="
try {{ (Invoke-WebRequest -UseBasicParsing -TimeoutSec 8 "http://127.0.0.1:8230/health").Content }} catch {{ $_.Exception.Message }}
Write-Host "`n=== IWR http://$ip`:8230/health (host LAN) ==="
try {{ (Invoke-WebRequest -UseBasicParsing -TimeoutSec 8 "http://$ip`:8230/health").Content }} catch {{ $_.Exception.Message }}
Write-Host "`n=== WSL ss 8230 (Ubuntu) ==="
& wsl -d Ubuntu -e sh -c "ss -tlnp 2>/dev/null | grep 8230 || true" 2>&1
Write-Host "`n=== WSL curl 127.0.0.1:8230/health ==="
& wsl -d Ubuntu -e sh -c "command -v curl >/dev/null && curl -sS -m 8 http://127.0.0.1:8230/health || echo no_curl" 2>&1
""".strip()


def _encoded_ps(script: str) -> str:
    b64 = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return f"powershell -NoProfile -NonInteractive -EncodedCommand {b64}"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _load_creds()
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    key_path = _ssh_key_path()
    rc = 0
    for host, label in HOSTS:
        user = _user_for_host(host)
        print("\n" + "=" * 60, f"\nLEGION {label}  {user}@{host}\n" + "=" * 60, flush=True)
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            if key_path is not None:
                c.connect(
                    host,
                    username=user,
                    key_filename=str(key_path),
                    timeout=30,
                    banner_timeout=20,
                    allow_agent=True,
                    look_for_keys=True,
                )
            else:
                if not pw:
                    print("No ~/.ssh/id_ed25519 and no VM_PASSWORD", file=sys.stderr)
                    return 1
                c.connect(
                    host,
                    username=user,
                    password=pw,
                    timeout=30,
                    banner_timeout=20,
                    look_for_keys=False,
                    allow_agent=False,
                )
        except Exception as ex:  # noqa: BLE001
            print("SSH connect failed:", ex, file=sys.stderr)
            rc = 1
            continue

        try:
            cmd = _encoded_ps(_ps_diag(host))
            _, stdout, stderr = c.exec_command(cmd, timeout=120)
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            print(out)
            if err.strip():
                print("STDERR:", err, file=sys.stderr)
        finally:
            c.close()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
