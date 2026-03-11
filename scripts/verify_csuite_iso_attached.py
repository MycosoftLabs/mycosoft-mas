#!/usr/bin/env python3
"""
Verify C-Suite VM ISO attachment: check that Win10 ISO exists on Proxmox 202
and that each VM (192, 193, 194, 195) has it attached to ide2.

Run this to diagnose why VMs still show Win11 installer when config says Win10.

Usage:
  python scripts/verify_csuite_iso_attached.py

Requires: PROXMOX202_PASSWORD or VM_PASSWORD in .credentials.local
Date: March 7, 2026
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    from infra.csuite.provision_base import load_credentials, load_proxmox_config
    from infra.csuite.provision_csuite import get_build_source
    from infra.csuite.provision_ssh import pve_ssh_exec

    creds = load_credentials()
    pwd = creds.get("proxmox202_password") or creds.get("proxmox_password") or creds.get("vm_password")
    if not (pwd or "").strip():
        print("ERROR: No Proxmox password. Set PROXMOX202_PASSWORD or VM_PASSWORD in .credentials.local")
        return 1

    cfg = load_proxmox_config()
    host = cfg.get("proxmox", {}).get("host", "192.168.0.202")
    vms = cfg.get("vms", {})
    vmids = [vms[r]["vmid"] for r in ("ceo", "cfo", "cto", "coo") if vms.get(r)]
    build_source = get_build_source()
    expected_iso = build_source.get("iso_path", "")
    windows_ver = cfg.get("build_source", {}).get("windows_version", "?")

    print("=" * 60)
    print("C-Suite ISO Verification")
    print("=" * 60)
    print(f"Host: {host}")
    print(f"Expected windows_version: {windows_ver}")
    print(f"Expected ISO (from config): {expected_iso}")
    print()

    # 1. List ISOs on Proxmox
    print("--- ISOs on Proxmox (local storage) ---")
    ok, out = pve_ssh_exec(
        host, "root", pwd,
        "ls -la /var/lib/vz/template/iso/ 2>/dev/null || echo 'Path not found or no access'",
        timeout=15,
    )
    if ok:
        for line in out.splitlines():
            if "Win" in line or "iso" in line or line.startswith("total"):
                print(line)
        if "Win10" not in out and expected_iso and "Win10" in expected_iso:
            print("\n⚠ WARNING: Win10 ISO not found in /var/lib/vz/template/iso/")
            print("  Run: python scripts/download_and_deploy_win10_iso.py")
    else:
        print(f"SSH failed: {out}")
        return 1

    # 2. Check each VM's ide2 and boot order
    print("\n--- VM config (ide2, boot) ---")
    for vmid in vmids:
        ok, out = pve_ssh_exec(
            host, "root", pwd,
            f"qm config {vmid} 2>/dev/null | grep -E '^ide2:|^boot:'",
            timeout=10,
        )
        role = next((r for r, c in vms.items() if c.get("vmid") == vmid), "?")
        if ok:
            lines = [l.strip() for l in out.splitlines() if l.strip()]
            ide2 = next((l for l in lines if l.startswith("ide2:")), "ide2: (not set)")
            boot = next((l for l in lines if l.startswith("boot:")), "boot: (not set)")
            match = "[OK]" if expected_iso and expected_iso.split("/")[-1] in (ide2 or "") else "[MISMATCH]"
            print(f"VM {vmid} ({role}): {ide2} | {boot} {match}")
        else:
            print(f"VM {vmid} ({role}): ERROR - {out}")

    print()
    print("If ide2 shows Win11 or is empty, run: CSUITE_USE_SSH=1 python scripts/fix_csuite_windows_install.py")
    print("If Win10 ISO is missing, run: python scripts/download_and_deploy_win10_iso.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
