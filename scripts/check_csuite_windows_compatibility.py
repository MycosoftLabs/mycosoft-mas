#!/usr/bin/env python3
"""
Check Proxmox 202 host and C-Suite VM hardware compatibility for Windows 11 vs Windows 10.

Windows 11 requires: UEFI (OVMF), TPM 2.0, EFI disk, CPU type host, Secure Boot capable.
Windows 10 works with: Legacy BIOS or UEFI, no TPM required — broader compatibility.

Runs checks via SSH to Proxmox 202. Recommends Windows 10 when Win11 requirements
may not be met, or when user explicitly needs compatibility with older hardware.

Usage:
  python scripts/check_csuite_windows_compatibility.py
  python scripts/check_csuite_windows_compatibility.py --force-win10   # always recommend Win10

Requires: PROXMOX202_PASSWORD or VM_PASSWORD in .credentials.local
Date: March 7, 2026
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("check-windows-compat")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check C-Suite Windows 10/11 compatibility on Proxmox 202")
    parser.add_argument("--force-win10", action="store_true", help="Always recommend Windows 10 (ignore hardware)")
    args = parser.parse_args()

    if args.force_win10:
        print("RECOMMENDATION: Windows 10 (--force-win10)")
        print("REASON: User requested Windows 10 for compatibility.")
        print("ACTION: Set windows_version: '10' in config/proxmox202_csuite.yaml")
        print("        Upload Win10 ISO to Proxmox (e.g. local:iso/Win10_22H2_English_x64.iso)")
        return 0

    from infra.csuite.provision_base import load_credentials, load_proxmox_config
    from infra.csuite.provision_ssh import pve_ssh_exec

    creds = load_credentials()
    pwd = creds.get("proxmox202_password") or creds.get("proxmox_password") or creds.get("vm_password")
    if not (pwd or "").strip():
        logger.error("No Proxmox password. Set PROXMOX202_PASSWORD or VM_PASSWORD in .credentials.local")
        return 1

    cfg = load_proxmox_config()
    pve = cfg.get("proxmox", {})
    host = pve.get("host", "192.168.0.202")

    checks: dict[str, tuple[bool, str]] = {}
    win11_ok = True

    # 1. CPU (host passthrough available)
    ok, out = pve_ssh_exec(host, "root", pwd, "qm config 0 2>/dev/null | grep -E '^cpu:' || echo 'N/A'", timeout=10)
    cpu_line = (out or "").strip()
    has_host_cpu = "host" in cpu_line or "kvm64" in cpu_line  # default is often host
    checks["CPU (host passthrough)"] = (True, "Proxmox supports host CPU passthrough" if has_host_cpu else "Check VM CPU config")

    # 2. OVMF (UEFI) available for Windows 11
    ok, out = pve_ssh_exec(
        host, "root", pwd,
        "ls -la /usr/share/OVMF/OVMF_CODE*.fd 2>/dev/null || ls -la /usr/share/pve-edk2-firmware/*.fd 2>/dev/null || echo 'NONE'",
        timeout=10,
    )
    has_ovmf = "fd" in (out or "").lower() and "NONE" not in (out or "")
    checks["OVMF (UEFI firmware)"] = (has_ovmf, "OVMF available for Win11" if has_ovmf else "OVMF may be missing — Win10 recommended")

    # 3. TPM support (swtpm or vTPM)
    ok, out = pve_ssh_exec(
        host, "root", pwd,
        "which swtpm 2>/dev/null || dpkg -l swtpm 2>/dev/null | grep -q swtpm && echo ok || echo 'not found'",
        timeout=10,
    )
    has_tpm = "ok" in (out or "").lower() or "swtpm" in (out or "").lower()
    checks["TPM 2.0 (swtpm)"] = (has_tpm, "swtpm available for Win11" if has_tpm else "TPM not detected — Win10 recommended")

    # 4. ISO storage — check if Win11 and/or Win10 ISO exist
    ok, out = pve_ssh_exec(
        host, "root", pwd,
        "pvesm list local 2>/dev/null | head -5; ls -la /var/lib/vz/template/iso/*.iso 2>/dev/null | head -10 || true",
        timeout=15,
    )
    iso_list = out or ""
    has_win11_iso = "win11" in iso_list.lower() or "Win11" in iso_list
    has_win10_iso = "win10" in iso_list.lower() or "Win10" in iso_list
    checks["Win11 ISO"] = (has_win11_iso, "Win11 ISO found" if has_win11_iso else "Upload Win11_24H2_English_x64.iso to Proxmox")
    checks["Win10 ISO"] = (has_win10_iso, "Win10 ISO found" if has_win10_iso else "Upload Win10_22H2_English_x64.iso for fallback")

    # Determine recommendation
    if not has_ovmf or not has_tpm:
        win11_ok = False

    print("=" * 60)
    print("C-Suite Windows Compatibility Check (Proxmox 202)")
    print("=" * 60)
    for name, (ok_, msg) in checks.items():
        status = "OK" if ok_ else "WARN"
        print(f"  [{status}] {name}: {msg}")
    print()

    if win11_ok and has_win11_iso:
        print("RECOMMENDATION: Windows 11")
        print("REASON: OVMF, TPM, and Win11 ISO detected. Host meets Win11 VM requirements.")
        print("ACTION: Keep windows_version: '11' in config/proxmox202_csuite.yaml")
    else:
        print("RECOMMENDATION: Windows 10")
        print("REASON: Win11 requirements may not be met (OVMF/TPM) or Win11 ISO missing.")
        print("        Windows 10 works on all Proxmox hosts — no TPM/UEFI required.")
        print("ACTION: Set windows_version: '10' in config/proxmox202_csuite.yaml")
        print("        Add iso_path_win10: 'local:iso/Win10_22H2_English_x64.iso'")
        print("        Upload Windows 10 ISO to Proxmox if not present.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
