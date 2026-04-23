#!/usr/bin/env python3
r"""
Deploy crep tile stub to Voice 192.168.0.241 and Earth-2 192.168.0.249 on port 8230.

- SFTP: C:\mycosoft\mas-tile-stub\services\crep_tile_render_stub\*.py
- pip install --user fastapi uvicorn
- Free port 8230, start uvicorn in a hidden process; optional inbound Windows firewall for TCP 8230

Legion 4080 boxes use local Windows accounts, not the VM *mycosoft* user:
- 192.168.0.241 (4080B Voice)  → default SSH user **owner1**
- 192.168.0.249 (4080A Earth-2) → default SSH user **owner2**

Override with env LEGION241_SSH_USER / LEGION249_SSH_USER. SSH: **~/.ssh/id_ed25519**
(LEGION_SSH_KEY) first; if no key, falls back to VM_PASSWORD (rare for these hosts).

Apr 17, 2026
"""
from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

import paramiko

REPO = Path(__file__).resolve().parent.parent
STUB = REPO / "services" / "crep_tile_render_stub"
WIN_ROOT = r"C:\mycosoft\mas-tile-stub"
HOSTS: tuple[tuple[str, str], ...] = (
    ("192.168.0.241", "density"),
    ("192.168.0.249", "earth2"),
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


def _ensure_remote_stub_dir(c: paramiko.SSHClient) -> None:
    """Create C:\\mycosoft\\... tree on Windows; SFTP mkdir alone is unreliable with OpenSSH."""
    p = r"C:\mycosoft\mas-tile-stub\services\crep_tile_render_stub"
    _, o, e = c.exec_command(f'cmd /c "mkdir {p} 2>nul"', timeout=30)
    o.read()
    e.read()


def _add_firewall_8230(c: paramiko.SSHClient) -> None:
    # Domain + Private + Public = same as New-NetFirewallRule -Profile Any (Morgan: LAN demos, category mismatch)
    ps = r"""
$ErrorActionPreference = 'SilentlyContinue'
$rule = 'Mycosoft-CREP-TileStub-TCP8230'
Get-NetFirewallRule -DisplayName $rule 2>$null | Remove-NetFirewallRule
$null = netsh advfirewall firewall delete rule name=$rule 2>$null
New-NetFirewallRule -DisplayName $rule -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8230 -Profile Domain,Private,Public
""".strip()
    _, o, e = c.exec_command(_encoded_ps(ps), timeout=60)
    o.read()
    e.read()


def _encoded_ps(script: str) -> str:
    b64 = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return f"powershell -NoProfile -NonInteractive -EncodedCommand {b64}"


def _deploy_one(host: str, profile: str, pw: str) -> int:
    user = _user_for_host(host)
    print("---", host, user, f"CREP_TILE_STUB_PROFILE={profile}", "---", flush=True)
    if not (STUB / "main.py").is_file():
        print("Missing stub at", STUB, file=sys.stderr)
        return 1

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key_path = _ssh_key_path()
    try:
        if key_path is not None:
            c.connect(
                host,
                username=user,
                key_filename=str(key_path),
                timeout=25,
                banner_timeout=20,
                allow_agent=True,
                look_for_keys=True,
            )
        else:
            if not pw:
                print("Need ~\\.ssh\\id_ed25519 (or LEGION_SSH_KEY) or VM_PASSWORD for", host, file=sys.stderr)
                return 1
            c.connect(
                host,
                username=user,
                password=pw,
                timeout=25,
                banner_timeout=20,
                look_for_keys=False,
                allow_agent=False,
            )
    except OSError as ex:
        print("ssh connect failed:", host, user, ex, file=sys.stderr)
        return 1
    except paramiko.ssh_exception.AuthenticationException as ex:
        print("ssh auth failed:", host, user, ex, file=sys.stderr)
        return 1

    try:
        _ensure_remote_stub_dir(c)
        _add_firewall_8230(c)
        s = c.open_sftp()
        rp = "C:/mycosoft/mas-tile-stub/services/crep_tile_render_stub"
        s.put(str(STUB / "main.py"), f"{rp}/main.py")
        s.put(str(STUB / "__init__.py"), f"{rp}/__init__.py")
        s.close()

        _, o, e = c.exec_command(
            'cmd /c "py -3 -m pip install --user -q fastapi uvicorn" 2>&1', timeout=600
        )
        o.read()
        e.read()
        c.exec_command('cmd /c "python -m pip install --user -q fastapi uvicorn" 2>&1', timeout=600)
        wroot = WIN_ROOT.replace("\\", "\\\\")
        ps = f"""
$ErrorActionPreference = "SilentlyContinue"
$root = "{wroot}"
$env:PYTHONPATH = $root
$env:CREP_TILE_STUB_PROFILE = "{profile}"
Get-NetTCPConnection -LocalPort 8230 -ErrorAction SilentlyContinue | ForEach-Object {{ try {{ Stop-Process -Id $_.OwningProcess -Force }} catch {{}} }}
$exe = (Get-Command py -ErrorAction SilentlyContinue).Path
if (-not $exe) {{ $exe = (Get-Command python -ErrorAction SilentlyContinue).Path }}
if (-not $exe) {{ throw "no python" }}
Start-Process -WindowStyle Hidden -FilePath $exe -ArgumentList "-m","uvicorn","services.crep_tile_render_stub.main:app","--host","0.0.0.0","--port","8230" -WorkingDirectory $root
Start-Sleep -Seconds 2
(Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 "http://127.0.0.1:8230/health" -ErrorAction SilentlyContinue).Content
""".strip()
        _, o2, e2 = c.exec_command(_encoded_ps(ps), timeout=60)
        out = o2.read().decode("utf-8", errors="replace")
        err = e2.read().decode("utf-8", errors="replace")
        print("stub:", (out + err)[:400])
    finally:
        c.close()
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _load_creds()
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    nbad = 0
    for h, prof in HOSTS:
        if _deploy_one(h, prof, pw) != 0:
            nbad += 1
    return 1 if nbad else 0


if __name__ == "__main__":
    raise SystemExit(main())
