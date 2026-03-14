#!/usr/bin/env python3
"""
Run Claude Cowork fix and watchdog on COO VM (192.168.0.195).

Connects via WinRM, pushes fix-claude-cowork-vm.ps1, ensure-cowork-vm-watchdog.ps1,
install-cowork-vm-watchdog.ps1, runs fix script, then installs the watchdog task.

Requires: pywinrm. Credentials from CSUITE_GUEST_PASSWORD or VM_PASSWORD.
Date: March 7, 2026
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("cowork-coo")


def main() -> int:
    # Load credentials
    cred_paths = [
        REPO_ROOT / ".credentials.local",
        REPO_ROOT / "config" / "proxmox202_credentials.env",
    ]
    for p in cred_paths:
        if p.exists():
            for line in p.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    ip = os.environ.get("COO_VM_IP", "192.168.0.195")
    ap = argparse.ArgumentParser(description="Setup Claude Cowork on COO VM via WinRM")
    ap.add_argument("--ip", default=ip, help=f"COO VM IP (default: {ip})")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.dry_run:
        logger.info("[DRY RUN] Would run Claude Cowork fix + watchdog on %s", args.ip)
        return 0

    sys.path.insert(0, str(REPO_ROOT))
    from infra.csuite.bootstrap_guest_remote import setup_claude_cowork_on_guest

    ok, msg = setup_claude_cowork_on_guest(args.ip)
    if ok:
        logger.info("%s", msg)
        return 0
    logger.error("%s", msg)
    return 1


if __name__ == "__main__":
    sys.exit(main())
