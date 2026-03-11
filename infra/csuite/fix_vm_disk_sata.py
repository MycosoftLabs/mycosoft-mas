#!/usr/bin/env python3
"""
Fix C-Suite VMs 192-195: convert scsi0 → sata0 so Windows installer sees disk.

Run on Proxmox host or from dev machine with API access.
C-Suite VMs run on Proxmox 202: host 192.168.0.202, node pve (per proxmox202_csuite.yaml).

Usage:
  python fix_vm_disk_sata.py [--dry-run] [--vmids 192,193,194,195]
  python fix_vm_disk_sata.py --use-ssh   # Use SSH fallback (qm set) when API fails

Ref: docs/CSUITE_WINDOWS_INSTALL_FIX_MAR07_2026.md
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Add infra/csuite for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))
from provision_base import (
    load_credentials,
    load_proxmox_config,
    pve_request,
    pve_stop_vm,
    pve_get_vm_config,
)
from provision_ssh import pve_ssh_exec
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# C-Suite runs on Proxmox 202 (192.168.0.202), node pve — per config/proxmox202_csuite.yaml
DEFAULT_NODE = "pve"
DEFAULT_HOST = "192.168.0.202"
DEFAULT_PORT = 8006
DEFAULT_VMIDS = [192, 193, 194, 195]


def _load_defaults() -> tuple[str, str, int]:
    """Load host, node, port from proxmox202_csuite.yaml. Fallback to module defaults."""
    cfg = load_proxmox_config()
    prox = cfg.get("proxmox", {}) or {}
    host = (prox.get("host") or DEFAULT_HOST).strip()
    node = (prox.get("node") or DEFAULT_NODE).strip()
    port = int(prox.get("port") or DEFAULT_PORT)
    return host, node, port


def _get_ssh_password(creds: dict) -> str:
    """Get Proxmox root password for SSH (proxmox202 > proxmox > vm)."""
    return (
        (creds.get("proxmox202_password") or "").strip()
        or (creds.get("proxmox_password") or "").strip()
        or (creds.get("vm_password") or "").strip()
    )


def _get_vm_config_ssh(vmid: int, host: str, creds: dict) -> tuple[bool, dict | str]:
    """Get VM config via SSH `qm config`. Returns (ok, cfg_dict_or_error)."""
    password = _get_ssh_password(creds)
    if not password:
        return False, "No Proxmox password for SSH"
    ok, out = pve_ssh_exec(host, "root", password, f"qm config {vmid}", timeout=15)
    if not ok:
        return False, out
    cfg: dict[str, str] = {}
    for line in out.splitlines():
        line = line.strip()
        if ":" in line:
            k, v = line.split(":", 1)
            cfg[k.strip()] = v.strip()
    return True, cfg


def fix_vm_disk_sata_ssh(
    vmid: int,
    host: str,
    creds: dict,
    dry_run: bool = False,
    scsi0_val: str | None = None,
    boot_new: str | None = None,
) -> tuple[bool, str]:
    """
    Convert VM scsi0 → sata0 via SSH qm commands. Use when API returns 401.
    Fetches config via SSH if scsi0_val/boot_new not provided.
    """
    password = _get_ssh_password(creds)
    if not password:
        return False, "No Proxmox password for SSH (set PROXMOX202_PASSWORD, PROXMOX_PASSWORD, or VM_PASSWORD)"

    if scsi0_val is None or boot_new is None:
        ok, raw = _get_vm_config_ssh(vmid, host, creds)
        if not ok or not isinstance(raw, dict):
            return False, f"Could not get VM config via SSH: {raw}"
        scsi0_val = raw.get("scsi0", "")
        if "sata0" in raw and not scsi0_val:
            return True, f"VM {vmid} already uses sata0"
        boot = raw.get("boot", "order=scsi0")
        boot_new = boot.replace("scsi0", "sata0") if scsi0_val else "order=sata0"
        if "ide2" in raw.get("boot", "") and "ide2" not in boot_new:
            boot_new = "order=ide2;sata0"

    if not scsi0_val:
        return False, f"VM {vmid} has no scsi0 — unknown disk setup"

    sata0_val = scsi0_val.replace(",iothread=1", "").strip()

    if dry_run:
        logger.info("[DRY RUN] SSH: qm stop %d; qm set %d --delete scsi0 --delete scsihw --sata0 ...", vmid, vmid)
        return True, "Dry run — no SSH changes made"

    # Stop VM
    ok, out = pve_ssh_exec(host, "root", password, f"qm stop {vmid} --skiplock", timeout=30)
    if not ok:
        logger.warning("qm stop %d: %s (continuing)", vmid, out)
    else:
        time.sleep(3)

    # Delete scsi0 and scsihw, add sata0 and boot (single qm set)
    cmd = f"qm set {vmid} --delete scsi0 --delete scsihw --sata0 '{sata0_val}' --boot '{boot_new}'"
    ok, out = pve_ssh_exec(host, "root", password, cmd, timeout=30)
    if not ok:
        return False, f"SSH qm set failed: {out}"
    return True, f"VM {vmid} converted scsi0 → sata0 via SSH, boot={boot_new}"


def fix_vm_disk_sata(
    vmid: int,
    node: str = DEFAULT_NODE,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    creds: dict | None = None,
    dry_run: bool = False,
    use_ssh: bool = False,
) -> tuple[bool, str]:
    """
    Convert VM from scsi0 to sata0 (keep same disk).
    When use_ssh=True, uses SSH qm commands instead of API.
    Returns (ok, message).
    """
    creds = creds or load_credentials()
    if use_ssh:
        return fix_vm_disk_sata_ssh(vmid, host, creds, dry_run=dry_run)

    ok, cfg = pve_get_vm_config(node, vmid, host, port, creds)
    if not ok or not isinstance(cfg, dict):
        return False, f"Could not get VM config: {cfg}"

    if "scsi0" not in cfg:
        if "sata0" in cfg:
            return True, f"VM {vmid} already uses sata0"
        return False, f"VM {vmid} has neither scsi0 nor sata0 — unknown disk setup"

    scsi0_val = cfg.pop("scsi0")
    # Remove scsihw if present (VirtIO SCSI)
    cfg.pop("scsihw", None)
    cfg["sata0"] = scsi0_val.replace(",iothread=1", "").strip()
    # Update boot order
    boot = cfg.get("boot", "")
    if "scsi0" in str(boot):
        cfg["boot"] = boot.replace("scsi0", "sata0")
    # Ensure ide2 first if ISO attached
    if "ide2" in cfg and "ide2" not in str(cfg.get("boot", "")):
        cfg["boot"] = "order=ide2;sata0"
    elif "boot" not in cfg or not cfg["boot"]:
        cfg["boot"] = "order=sata0"

    if dry_run:
        logger.info("[DRY RUN] VM %d would be updated: scsi0 → sata0, boot=%s", vmid, cfg.get("boot"))
        return True, "Dry run — no changes made"

    sata0_val = scsi0_val.replace(",iothread=1", "").strip()
    boot_new = (cfg.get("boot") or "order=sata0").replace("scsi0", "sata0")
    if "ide2" in cfg and "ide2" not in str(boot_new):
        boot_new = "order=ide2;sata0"

    # Stop VM first
    ok_stop, _ = pve_stop_vm(node, vmid, host, port, creds, force=True)
    if ok_stop:
        time.sleep(3)

    # Single PUT: delete scsi0,scsihw (only keys that exist) — Proxmox accepts comma-separated
    delete_list = [k for k in ["scsi0", "scsihw"] if k in (pve_get_vm_config(node, vmid, host, port, creds)[1] or {})]
    if delete_list:
        ok_del, result = pve_request(
            f"/nodes/{node}/qemu/{vmid}/config",
            host=host,
            port=port,
            method="PUT",
            data={"delete": ",".join(delete_list)},
            creds=creds,
        )
        if not ok_del:
            return False, f"Failed to delete {','.join(delete_list)}: {result}"

    # Add sata0 and update boot
    ok_put, result = pve_request(
        f"/nodes/{node}/qemu/{vmid}/config",
        host=host,
        port=port,
        method="PUT",
        data={"sata0": sata0_val, "boot": boot_new},
        creds=creds,
    )
    if not ok_put:
        return False, str(result)

    return True, f"VM {vmid} converted scsi0 → sata0, boot={boot_new}. Start VM to boot Windows installer."


def main() -> int:
    ap = argparse.ArgumentParser(description="Fix C-Suite VMs: scsi0 → sata0 for Windows install")
    ap.add_argument("--dry-run", action="store_true", help="Show what would change, do not apply")
    ap.add_argument("--use-ssh", action="store_true", help="Use SSH (qm) instead of Proxmox API")
    ap.add_argument("--vmids", default=",".join(map(str, DEFAULT_VMIDS)), help="Comma-separated VM IDs")
    ap.add_argument("--node", default=None, help="Proxmox node (default from config)")
    ap.add_argument("--host", default=None, help="Proxmox host (default from config)")
    ap.add_argument("--port", type=int, default=None, help="Proxmox port (default from config)")
    args = ap.parse_args()
    host, node, port = _load_defaults()
    if args.host is not None:
        host = args.host
    if args.node is not None:
        node = args.node
    if args.port is not None:
        port = args.port
    vmids = [int(x.strip()) for x in args.vmids.split(",") if x.strip()]

    creds = load_credentials()
    failed = 0
    for vmid in vmids:
        ok, msg = fix_vm_disk_sata(
            vmid, node, host, port, creds, args.dry_run, use_ssh=args.use_ssh
        )
        logger.info("VM %d: %s", vmid, msg)
        if not ok:
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
