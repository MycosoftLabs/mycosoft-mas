#!/usr/bin/env python3
"""
Fix C-Suite VMs: attach Windows 10/11 ISO and set boot order so each VM boots
to the Windows installer instead of an empty disk (which causes boot loop).

Also provisions COO VM (195) if it does not exist.

Uses Proxmox API when available; falls back to SSH (qm commands) on 401/API failure.

Usage:
  python scripts/fix_csuite_windows_install.py
  python scripts/fix_csuite_windows_install.py --dry-run
  CSUITE_USE_SSH=1 python scripts/fix_csuite_windows_install.py   # force SSH path

Requires: PROXMOX202_PASSWORD or VM_PASSWORD in .credentials.local
Date: March 7, 2026
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("fix-csuite-windows")


def _use_ssh() -> bool:
    return os.environ.get("CSUITE_USE_SSH", "").strip().lower() in ("1", "true", "yes")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix C-Suite VMs: attach Windows ISO, set boot order")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    args = parser.parse_args()

    from infra.csuite.provision_base import (
        load_credentials,
        load_proxmox_config,
        pve_request,
        pve_attach_iso_and_set_boot,
    )
    from infra.csuite.provision_csuite import create_windows_vm, get_build_source
    from infra.csuite.provision_ssh import pve_ssh_list_resources, pve_ssh_attach_iso_and_set_boot

    creds = load_credentials()
    pwd = creds.get("proxmox202_password") or creds.get("proxmox_password") or creds.get("vm_password")
    if not (pwd or "").strip():
        logger.error("No Proxmox password. Set PROXMOX202_PASSWORD or VM_PASSWORD in .credentials.local")
        return 1

    cfg = load_proxmox_config()
    pve = cfg.get("proxmox", {})
    host = pve.get("host", "192.168.0.202")
    port = int(pve.get("port", 8006))
    node = pve.get("node", "pve")

    build_source = get_build_source()
    iso_path = build_source.get("iso_path")
    logger.info("Build source: windows_version=%s, iso_path=%s", cfg.get("build_source", {}).get("windows_version"), iso_path)
    if not iso_path:
        logger.error("No iso_path in config. Set build_source.iso_path or iso_path_win10 in config/proxmox202_csuite.yaml")
        return 1

    vms = cfg.get("vms", {})
    vmids = [vms[r]["vmid"] for r in ("ceo", "cto", "cfo", "coo") if vms.get(r)]

    # Decide API vs SSH
    use_ssh = _use_ssh()
    existing: dict[int, dict] = {}

    if use_ssh:
        logger.info("Using SSH path (CSUITE_USE_SSH=1)")
        ok, data = pve_ssh_list_resources(host, "root", pwd)
        if not ok:
            logger.error("SSH list VMs failed: %s", data)
            return 1
        for v in data or []:
            if isinstance(v, dict) and v.get("type") == "qemu":
                try:
                    existing[int(v["vmid"])] = v
                except (TypeError, ValueError):
                    pass
    else:
        ok, vm_list = pve_request(
            "/cluster/resources?type=vm",
            host=host,
            port=port,
            creds=creds,
        )
        if not ok:
            logger.warning("API list VMs failed: %s — falling back to SSH", vm_list)
            os.environ["CSUITE_USE_SSH"] = "1"
            use_ssh = True
            ok, data = pve_ssh_list_resources(host, "root", pwd)
            if not ok:
                logger.error("SSH list VMs failed: %s", data)
                return 1
            for v in data or []:
                if isinstance(v, dict) and v.get("type") == "qemu":
                    try:
                        existing[int(v["vmid"])] = v
                    except (TypeError, ValueError):
                        pass
        else:
            qemu = [v for v in (vm_list or []) if isinstance(v, dict) and v.get("type") == "qemu"]
            existing = {int(v["vmid"]): v for v in qemu}

    logger.info("Existing VMs: %s", sorted(existing.keys()))

    # 1. Provision COO if missing
    if 195 not in existing:
        logger.info("COO VM (195) not found — provisioning...")
        if args.dry_run:
            logger.info("[DRY RUN] Would provision COO")
        else:
            if use_ssh:
                os.environ["CSUITE_USE_SSH"] = "1"
            ok_prov, msg = create_windows_vm("coo", dry_run=False, force_blank=True)
            if ok_prov:
                logger.info("COO provisioned: %s", msg)
                existing[195] = {"vmid": 195}
            else:
                logger.error("COO provision failed: %s", msg)
                return 1

    # 2. For each VM: attach ISO and set boot order
    for vmid in vmids:
        if vmid not in existing:
            logger.warning("VM %d not found — skipping", vmid)
            continue

        role_name = next((r for r, c in vms.items() if c.get("vmid") == vmid), str(vmid))

        if args.dry_run:
            logger.info("[DRY RUN] Would attach ISO and set boot for VM %d (%s)", vmid, role_name)
            continue

        logger.info("Fixing VM %d (%s): attach ISO, set boot order...", vmid, role_name)
        ok, msg = False, ""
        if use_ssh:
            ok, msg = pve_ssh_attach_iso_and_set_boot(
                host=host,
                vmid=vmid,
                iso_volid=iso_path,
                user="root",
                password=pwd,
            )
        else:
            ok, msg = pve_attach_iso_and_set_boot(
                node=node,
                vmid=vmid,
                iso_volid=iso_path,
                host=host,
                port=port,
                creds=creds,
            )
        if not ok and not use_ssh:
            logger.warning("  API attach failed, retrying via SSH...")
            ok, msg = pve_ssh_attach_iso_and_set_boot(
                host=host,
                vmid=vmid,
                iso_volid=iso_path,
                user="root",
                password=pwd,
            )
            if ok:
                use_ssh = True
        if ok:
            logger.info("  OK: %s", msg)
        else:
            logger.error("  FAILED: %s", msg)
            return 1

    logger.info("Done. Each VM will boot from Windows installer. Complete setup in Proxmox console.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
