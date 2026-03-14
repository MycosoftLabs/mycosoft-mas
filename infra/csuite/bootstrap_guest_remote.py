#!/usr/bin/env python3
"""
Host-driven Windows guest bootstrap via WinRM.

Waits for WinRM on the guest, pushes role_config.json and scripts, then runs
bootstrap, apply_role_manifest, and csuite_heartbeat -RegisterTask.

Requires: pywinrm. Credentials from CSUITE_GUEST_USER, CSUITE_GUEST_PASSWORD (or VM_PASSWORD).
Date: March 7, 2026
"""
from __future__ import annotations

import argparse
import base64
import logging
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
INFRA_CSUITE = REPO_ROOT / "infra" / "csuite"
CONFIG_DIR = REPO_ROOT / "config"

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("bootstrap-guest")


def _load_yaml(path: Path) -> dict:
    try:
        import yaml
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _get_bootstrap_config() -> dict:
    cfg = _load_yaml(CONFIG_DIR / "proxmox202_csuite.yaml")
    return cfg.get("bootstrap") or {}


def _wait_for_winrm(host: str, port: int, timeout_sec: int, retry_interval_sec: int) -> bool:
    import socket
    end = time.time() + timeout_sec
    while time.time() < end:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((host, port))
            s.close()
            return True
        except (socket.error, OSError):
            pass
        time.sleep(retry_interval_sec)
    return False


def _write_file_via_winrm(session, dest_path: str, content: str) -> bool:
    """Write content to dest_path on the guest. Content is UTF-8."""
    b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
    escaped = dest_path.replace("\\", "\\\\").replace('"', '`"')
    ps = f'''
$dir = [System.IO.Path]::GetDirectoryName("{escaped}")
if (-not (Test-Path $dir)) {{ New-Item -ItemType Directory -Path $dir -Force | Out-Null }}
$b64 = "{b64}"
$bytes = [Convert]::FromBase64String($b64)
[System.IO.File]::WriteAllBytes("{escaped}", $bytes)
'''
    try:
        r = session.run_ps(ps)
        return r.status_code == 0
    except Exception as e:
        logger.error("Failed to write %s: %s", dest_path, e)
        return False


def bootstrap_guest(role: str, ip: str, dry_run: bool = False) -> tuple[bool, str]:
    """
    Bootstrap a Windows guest at `ip` for the given role.
    Returns (success, message).
    """
    try:
        import winrm
    except ImportError:
        return False, "pywinrm not installed. Run: poetry add --group dev pywinrm"

    cfg = _get_bootstrap_config()
    user_env = cfg.get("guest_user_env") or "CSUITE_GUEST_USER"
    pass_env = cfg.get("guest_password_env") or "CSUITE_GUEST_PASSWORD"
    user_default = cfg.get("guest_user_default") or "Administrator"
    port = int(cfg.get("winrm_port") or 5985)
    timeout = int(cfg.get("connect_timeout_sec") or 300)
    retry_int = int(cfg.get("connect_retry_interval_sec") or 10)

    user = os.environ.get(user_env) or user_default
    password = os.environ.get(pass_env) or os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    if not password:
        return False, f"Set {pass_env} or VM_PASSWORD in .credentials.local"

    if dry_run:
        logger.info("[DRY RUN] Would bootstrap %s at %s:%d as %s", role, ip, port, user)
        return True, "Dry run — no bootstrap"

    logger.info("Waiting for WinRM on %s:%d (timeout %ds)...", ip, port, timeout)
    if not _wait_for_winrm(ip, port, timeout, retry_int):
        return False, f"WinRM not reachable on {ip}:{port} within {timeout}s"

    endpoint = f"http://{ip}:{port}/wsman"
    try:
        session = winrm.Session(endpoint, auth=(user, password), transport="ntlm")
    except Exception as e:
        return False, f"WinRM session failed: {e}"

    # Generate role_config.json on host and push to guest
    sys.path.insert(0, str(REPO_ROOT))
    from infra.csuite.provision_base import load_credentials
    from infra.csuite.emit_role_config import emit_role_config

    # Load proxmox202_credentials.env so PROXMOX202_*_TOKEN vars are set for emit_role_config
    load_credentials()

    import json
    merged = emit_role_config(role, None)
    config_content = json.dumps(merged, indent=2)
    # Guest path: C:\Users\<user>\AppData\Local\Mycosoft\C-Suite
    csuite_root = os.path.join("C:\\Users", user, "AppData\\Local", "Mycosoft", "C-Suite")
    config_path = os.path.join(csuite_root, "config", "role_config.json")
    scripts_path = os.path.join(csuite_root, "scripts")

    # Create dirs and push config
    base_esc = csuite_root.replace("\\", "\\\\")
    ps_mkdir = f'''
$base = "{base_esc}"
$configDir = Join-Path $base "config"
$scriptsDir = Join-Path $base "scripts"
New-Item -ItemType Directory -Path $configDir -Force | Out-Null
New-Item -ItemType Directory -Path $scriptsDir -Force | Out-Null
'''
    r = session.run_ps(ps_mkdir)
    if r.status_code != 0:
        return False, f"Failed to create dirs: {r.std_err}"

    if not _write_file_via_winrm(session, config_path, config_content):
        return False, "Failed to push role_config.json"

    # Push scripts
    scripts = [
        ("bootstrap_openclaw_windows.ps1", INFRA_CSUITE / "bootstrap_openclaw_windows.ps1"),
        ("apply_role_manifest.ps1", INFRA_CSUITE / "apply_role_manifest.ps1"),
        ("csuite_heartbeat.ps1", INFRA_CSUITE / "csuite_heartbeat.ps1"),
    ]
    if role.lower() == "cto":
        scripts.append(("bootstrap_cto_guest.ps1", INFRA_CSUITE / "bootstrap_cto_guest.ps1"))
    for name, src in scripts:
        if not src.exists():
            logger.warning("Script %s not found — skipping", src)
            continue
        content = src.read_text(encoding="utf-8")
        dest = os.path.join(scripts_path, name)
        if not _write_file_via_winrm(session, dest, content):
            return False, f"Failed to push {name}"

    # Run bootstrap, apply manifest, register heartbeat
    role_arg = role.upper()
    scripts_esc = scripts_path.replace("\\", "\\\\")
    mas_url = os.environ.get("MAS_API_URL", "http://192.168.0.188:8001")
    mindex_url = os.environ.get("MINDEX_API_URL", "http://192.168.0.189:8000")
    cto_code_root = "C:\\Users\\Administrator\\Mycosoft\\CODE"
    cto_git_org = "MycosoftLabs"
    if role.lower() == "cto":
        csuite_cfg = _load_yaml(CONFIG_DIR / "proxmox202_csuite.yaml")
        cto_ws = csuite_cfg.get("cto_workspace") or {}
        cto_code_root = cto_ws.get("code_root") or cto_code_root
        cto_git_org = cto_ws.get("git_org") or cto_git_org
    ps_run = f'''
$scriptsDir = "{scripts_esc}"
$env:CSUITE_ROLE = "{role}"
& "$scriptsDir\\bootstrap_openclaw_windows.ps1" -Role {role_arg}
if ($LASTEXITCODE -ne 0) {{ exit $LASTEXITCODE }}
& "$scriptsDir\\apply_role_manifest.ps1" -Role {role_arg}
if ($LASTEXITCODE -ne 0) {{ exit $LASTEXITCODE }}
& "$scriptsDir\\csuite_heartbeat.ps1" -RegisterTask
if ($LASTEXITCODE -ne 0) {{ exit $LASTEXITCODE }}
'''
    if role.lower() == "cto":
        cto_code_esc = cto_code_root.replace("\\", "\\\\")
        mas_repo = f"{cto_code_root}\\MAS\\mycosoft-mas"
        ps_run += f'''
$env:MAS_API_URL = "{mas_url}"
$env:MINDEX_API_URL = "{mindex_url}"
$env:CTO_CODE_ROOT = "{cto_code_esc}"
$env:CTO_GIT_ORG = "{cto_git_org}"
& "$scriptsDir\\bootstrap_cto_guest.ps1"
if ($LASTEXITCODE -ne 0) {{ exit $LASTEXITCODE }}
$installWatchdog = "{mas_repo}\\scripts\\install-cto-vm-watchdog.ps1"
if (Test-Path $installWatchdog) {{
    & $installWatchdog
}}
'''
    r = session.run_ps(ps_run)
    if r.status_code != 0:
        return False, f"Bootstrap failed: {r.std_err or r.std_out}"

    return True, f"Bootstrap completed for {role} at {ip}"


def setup_claude_cowork_on_guest(ip: str) -> tuple[bool, str]:
    """
    Push Claude Cowork fix + watchdog scripts to guest and run them.
    Used for COO VM (192.168.0.195) or any VM needing Cowork VM service fix.
    """
    try:
        import winrm
    except ImportError:
        return False, "pywinrm not installed. Run: poetry add --group dev pywinrm"

    cfg = _get_bootstrap_config()
    user_env = cfg.get("guest_user_env") or "CSUITE_GUEST_USER"
    pass_env = cfg.get("guest_password_env") or "CSUITE_GUEST_PASSWORD"
    user_default = cfg.get("guest_user_default") or "Administrator"
    port = int(cfg.get("winrm_port") or 5985)
    timeout = int(cfg.get("connect_timeout_sec") or 300)
    retry_int = int(cfg.get("connect_retry_interval_sec") or 10)

    user = os.environ.get(user_env) or user_default
    password = os.environ.get(pass_env) or os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    if not password:
        return False, f"Set {pass_env} or VM_PASSWORD in .credentials.local"

    logger.info("Waiting for WinRM on %s:%d (timeout %ds)...", ip, port, timeout)
    if not _wait_for_winrm(ip, port, timeout, retry_int):
        return False, f"WinRM not reachable on {ip}:{port} within {timeout}s"

    endpoint = f"http://{ip}:{port}/wsman"
    try:
        session = winrm.Session(endpoint, auth=(user, password), transport="ntlm")
    except Exception as e:
        return False, f"WinRM session failed: {e}"

    # Push cowork scripts to C:\Users\<user>\AppData\Local\Mycosoft\C-Suite\scripts\cowork
    cowork_scripts_dir = Path(REPO_ROOT) / "scripts"
    scripts = [
        ("fix-claude-cowork-vm.ps1", cowork_scripts_dir / "fix-claude-cowork-vm.ps1"),
        ("ensure-cowork-vm-watchdog.ps1", cowork_scripts_dir / "ensure-cowork-vm-watchdog.ps1"),
        ("install-cowork-vm-watchdog.ps1", cowork_scripts_dir / "install-cowork-vm-watchdog.ps1"),
    ]
    cowork_path = os.path.join("C:\\Users", user, "AppData\\Local", "Mycosoft", "C-Suite", "scripts", "cowork")
    base_esc = cowork_path.replace("\\", "\\\\")
    r = session.run_ps(f'New-Item -ItemType Directory -Path "{base_esc}" -Force | Out-Null')
    if r.status_code != 0:
        return False, f"Failed to create cowork dir: {r.std_err}"

    for name, src in scripts:
        if not src.exists():
            return False, f"Script not found: {src}"
        dest = os.path.join(cowork_path, name)
        if not _write_file_via_winrm(session, dest, src.read_text(encoding="utf-8")):
            return False, f"Failed to push {name}"

    # Run fix script (starts CoworkVMService, optionally clears cache)
    fix_esc = cowork_path.replace("\\", "\\\\")
    r = session.run_ps(f'& "{fix_esc}\\fix-claude-cowork-vm.ps1" -Force')
    if r.status_code != 0:
        logger.warning("Fix script returned %d: %s", r.status_code, r.std_err or r.std_out)

    # Install watchdog scheduled task (requires Admin - session is as Administrator)
    r = session.run_ps(f'& "{fix_esc}\\install-cowork-vm-watchdog.ps1"')
    if r.status_code != 0:
        return False, f"Watchdog install failed: {r.std_err or r.std_out}"

    return True, f"Claude Cowork fix + watchdog installed on {ip}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Bootstrap C-Suite Windows guest via WinRM")
    ap.add_argument("--role", "-r", required=True, choices=["ceo", "cfo", "cto", "coo"])
    ap.add_argument("--ip", required=True, help="Guest IP address")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ok, msg = bootstrap_guest(args.role, args.ip, dry_run=args.dry_run)
    if ok:
        logger.info("%s", msg)
        return 0
    logger.error("%s", msg)
    return 1


if __name__ == "__main__":
    sys.exit(main())
