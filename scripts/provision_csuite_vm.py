#!/usr/bin/env python3
"""
Provision C-Suite executive assistant VMs on Proxmox 90.

Usage:
  python scripts/provision_csuite_vm.py --role ceo
  python scripts/provision_csuite_vm.py --role cfo --dry-run
  python scripts/provision_csuite_vm.py --role all

Roles: ceo, cfo, cto, coo, all
Date: March 7, 2026
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add repo root for imports
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from infra.csuite.bootstrap_guest_remote import bootstrap_guest
from infra.csuite.provision_csuite import create_windows_vm, get_all_roles, get_role_config

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("provision-csuite")


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision C-Suite VMs on Proxmox 90")
    parser.add_argument(
        "--role",
        choices=["ceo", "cfo", "cto", "coo", "all"],
        required=True,
        help="Role to provision",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without creating")
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="After VM creation, run host-driven guest bootstrap via WinRM (OpenClaw, role manifest, heartbeat task)",
    )
    args = parser.parse_args()

    roles = get_all_roles() if args.role == "all" else [args.role]
    if not roles:
        logger.error("No roles configured. Check config/proxmox202_csuite.yaml")
        return 1

    failed = []
    for role in roles:
        cfg = get_role_config(role)
        if not cfg:
            logger.warning("Role %s not in config — skipping", role)
            continue
        ok, msg = create_windows_vm(role, dry_run=args.dry_run)
        if ok:
            logger.info("[%s] %s", role.upper(), msg)
        else:
            logger.error("[%s] %s", role.upper(), msg)
            failed.append(role)
            continue

        if args.bootstrap and not args.dry_run:
            ip = cfg.get("ip")
            if not ip:
                logger.warning("[%s] No IP in config — skipping bootstrap", role.upper())
                continue
            logger.info("[%s] Running host-driven bootstrap at %s...", role.upper(), ip)
            bok, bmsg = bootstrap_guest(role, ip, dry_run=False)
            if bok:
                logger.info("[%s] Bootstrap: %s", role.upper(), bmsg)
            else:
                logger.error("[%s] Bootstrap failed: %s", role.upper(), bmsg)
                failed.append(role)

    if failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
