#!/usr/bin/env python3
"""
Download Windows 10 22H2 ISO via Fido.ps1, copy to Proxmox 202, update config,
and run fix_csuite_windows_install so all C-Suite VMs boot from the installer.

Runs fully automated — no manual steps.

Usage:
  python scripts/download_and_deploy_win10_iso.py
  python scripts/download_and_deploy_win10_iso.py --skip-download   # ISO already local
  python scripts/download_and_deploy_win10_iso.py --skip-fix       # Don't run fix script

Requires: PROXMOX202_PASSWORD or VM_PASSWORD in .credentials.local
Date: March 7, 2026
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("win10-iso-deploy")

FIDO_URL = "https://raw.githubusercontent.com/pbatard/Fido/master/Fido.ps1"
FIDO_SCRIPT = REPO_ROOT / "scripts" / "Fido.ps1"
DATA_ISO_DIR = REPO_ROOT / "data" / "iso"
LOCAL_ISO = DATA_ISO_DIR / "Win10_22H2_English_x64.iso"
PROXMOX_HOST = "192.168.0.202"
PROXMOX_ISO_PATH = "/var/lib/vz/template/iso/Win10_22H2_English_x64.iso"
CONFIG_PATH = REPO_ROOT / "config" / "proxmox202_csuite.yaml"


def load_credentials() -> dict[str, str]:
    """Load credentials from .credentials.local etc."""
    from infra.csuite.provision_base import load_credentials as _load
    return _load()


def fetch_fido() -> bool:
    """Download Fido.ps1 if not present."""
    if FIDO_SCRIPT.exists():
        logger.info("Fido.ps1 already at %s", FIDO_SCRIPT)
        return True
    try:
        import urllib.request
        DATA_ISO_DIR.parent.mkdir(parents=True, exist_ok=True)
        FIDO_SCRIPT.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Fetching Fido.ps1 from %s ...", FIDO_URL)
        urllib.request.urlretrieve(FIDO_URL, FIDO_SCRIPT)
        logger.info("Fido.ps1 saved to %s", FIDO_SCRIPT)
        return True
    except Exception as e:
        logger.error("Failed to fetch Fido.ps1: %s", e)
        return False


def get_win10_iso_url() -> str | None:
    """Run Fido -GetUrl to obtain the Windows 10 22H2 download URL."""
    if not FIDO_SCRIPT.exists():
        if not fetch_fido():
            return None
    args = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(FIDO_SCRIPT),
        "-Win", "Windows 10",
        "-Rel", "22H2",
        "-Ed", "Pro",
        "-Lang", "English",
        "-Arch", "x64",
        "-GetUrl",
    ]
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(REPO_ROOT),
            encoding="utf-8",
            errors="replace",
        )
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        # URL is typically the last non-empty line or a line starting with http
        for line in (out + "\n" + err).splitlines():
            line = line.strip()
            if line.startswith("http") and "microsoft.com" in line.lower():
                return line
        # Fallback: any http URL in output
        m = re.search(r"https?://[^\s\"'\\)]+", out + err)
        if m:
            return m.group(0)
        logger.error("Fido did not return a URL. stdout=%r stderr=%r", out[:500], err[:500])
        return None
    except subprocess.TimeoutExpired:
        logger.error("Fido timed out")
        return None
    except Exception as e:
        logger.error("Fido failed: %s", e)
        return None


def download_iso(url: str) -> bool:
    """Download ISO from URL to LOCAL_ISO."""
    DATA_ISO_DIR.mkdir(parents=True, exist_ok=True)
    try:
        import urllib.request
        logger.info("Downloading Win10 ISO from %s ... (this may take several minutes)", url[:80])
        urllib.request.urlretrieve(url, LOCAL_ISO)
        size_mb = LOCAL_ISO.stat().st_size / (1024 * 1024)
        logger.info("Downloaded %.1f MB to %s", size_mb, LOCAL_ISO)
        return size_mb > 100  # sanity: ISO should be >100 MB
    except Exception as e:
        logger.error("Download failed: %s", e)
        return False


def scp_iso_to_proxmox(password: str) -> bool:
    """Copy ISO to Proxmox 202 via SCP (paramiko SFTP or pscp/plink)."""
    pwd = (password or "").strip().strip('"').strip("'")
    if not pwd:
        logger.error("No Proxmox password for SCP")
        return False

    # Prefer paramiko SFTP
    try:
        import paramiko
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            PROXMOX_HOST,
            username="root",
            password=pwd,
            timeout=30,
            auth_timeout=30,
            banner_timeout=30,
        )
        sftp = client.open_sftp()
        remote_dir = os.path.dirname(PROXMOX_ISO_PATH)
        # Ensure remote dir exists
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            sftp.mkdir(remote_dir)
        logger.info("Uploading %s to root@%s:%s ...", LOCAL_ISO.name, PROXMOX_HOST, PROXMOX_ISO_PATH)
        sftp.put(str(LOCAL_ISO), PROXMOX_ISO_PATH)
        sftp.close()
        client.close()
        logger.info("Upload complete")
        return True
    except ImportError:
        pass
    except Exception as e:
        logger.warning("Paramiko SFTP failed: %s — trying pscp", e)

    # Fallback: pscp (PuTTY)
    pscp = "pscp" if sys.platform != "win32" else "pscp.exe"
    import shutil
    pscp_path = shutil.which(pscp)
    if pscp_path:
        cmd = [
            pscp_path, "-batch", "-pw", pwd,
            str(LOCAL_ISO),
            f"root@{PROXMOX_HOST}:{PROXMOX_ISO_PATH}",
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if proc.returncode == 0:
                logger.info("Upload complete (pscp)")
                return True
            logger.error("pscp failed: %s", proc.stderr or proc.stdout)
        except Exception as e:
            logger.error("pscp failed: %s", e)
    else:
        logger.error("Neither paramiko nor pscp available. pip install paramiko")
    return False


def update_config_windows_10() -> bool:
    """Set windows_version to '10' in config."""
    if not CONFIG_PATH.exists():
        logger.error("Config not found: %s", CONFIG_PATH)
        return False
    text = CONFIG_PATH.read_text(encoding="utf-8")
    old = 'windows_version: "11"'
    new = 'windows_version: "10"'
    if new in text:
        logger.info("Config already has windows_version: \"10\"")
        return True
    if old not in text:
        # Try alternate pattern
        text2 = re.sub(r'windows_version:\s*["\']11["\']', new, text)
        if text2 == text:
            logger.error("Could not find windows_version in config")
            return False
        text = text2
    else:
        text = text.replace(old, new)
    CONFIG_PATH.write_text(text, encoding="utf-8")
    logger.info("Updated %s to windows_version: \"10\"", CONFIG_PATH.name)
    return True


def run_fix_script() -> bool:
    """Run fix_csuite_windows_install.py."""
    fix_script = REPO_ROOT / "scripts" / "fix_csuite_windows_install.py"
    if not fix_script.exists():
        logger.error("Fix script not found: %s", fix_script)
        return False
    logger.info("Running fix_csuite_windows_install.py ...")
    proc = subprocess.run(
        [sys.executable, str(fix_script)],
        cwd=str(REPO_ROOT),
        timeout=120,
    )
    if proc.returncode != 0:
        logger.error("Fix script exited with code %d", proc.returncode)
        return False
    logger.info("Fix script completed successfully")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Win10 ISO, deploy to Proxmox 202, fix C-Suite VMs")
    parser.add_argument("--skip-download", action="store_true", help="ISO already at data/iso/Win10_22H2_English_x64.iso")
    parser.add_argument("--skip-fix", action="store_true", help="Do not run fix_csuite_windows_install")
    parser.add_argument("--force", action="store_true", help="Force re-download even if ISO exists")
    args = parser.parse_args()

    creds = load_credentials()
    pwd = creds.get("proxmox202_password") or creds.get("proxmox_password") or creds.get("vm_password")
    if not (pwd or "").strip():
        logger.error("No Proxmox password. Set PROXMOX202_PASSWORD or VM_PASSWORD in .credentials.local")
        return 1

    # 1. Download ISO (unless skipped or already present and valid)
    if not args.skip_download:
        if LOCAL_ISO.exists() and not args.force:
            size_mb = LOCAL_ISO.stat().st_size / (1024 * 1024)
            if size_mb > 100:
                logger.info("Local ISO exists (%.1f MB). Skipping download. Use --force to re-download.", size_mb)
                args.skip_download = True
        if not args.skip_download:
            url = get_win10_iso_url()
            if not url:
                return 1
            if not download_iso(url):
                return 1
    else:
        if not LOCAL_ISO.exists():
            logger.error("--skip-download but %s does not exist", LOCAL_ISO)
            return 1
        logger.info("Using existing ISO at %s", LOCAL_ISO)

    # 2. Copy to Proxmox 202
    if not scp_iso_to_proxmox(pwd):
        return 1

    # 3. Update config
    if not update_config_windows_10():
        return 1

    # 4. Run fix script
    if not args.skip_fix:
        if not run_fix_script():
            return 1

    logger.info("Done. C-Suite VMs (CEO, CFO, CTO, COO) will boot from Windows 10 installer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
