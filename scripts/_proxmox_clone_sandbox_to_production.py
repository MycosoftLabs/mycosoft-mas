#!/usr/bin/env python3
"""
Clone Sandbox VM (187) to Production VM (186) via Proxmox API.
Phase 1 of mycosoft.org Production VM Clone CI/CD plan.
Date: March 13, 2026
"""
from __future__ import annotations

import os
import sys
import time
import urllib3
from pathlib import Path

# Load credentials
REPO = Path(__file__).resolve().parent.parent
for f in (REPO / ".credentials.local", REPO.parent / "website" / ".credentials.local"):
    if f.exists():
        for line in f.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

urllib3.disable_warnings()
import requests

PROXMOX_HOST = os.environ.get("PROXMOX_HOST", "192.168.0.202")
PROXMOX_PORT = 8006
PROXMOX_USER = "root@pam"
PROXMOX_PASS = os.environ.get("PROXMOX202_PASSWORD") or os.environ.get("PROXMOX_PASSWORD")
SOURCE_VMID = int(os.environ.get("SANDBOX_PROXMOX_VMID", "187"))  # Sandbox VMID in Proxmox
TARGET_VMID = 186
TARGET_NAME = "production-website"


def get_ticket():
    r = requests.post(
        f"https://{PROXMOX_HOST}:{PROXMOX_PORT}/api2/json/access/ticket",
        data={"username": PROXMOX_USER, "password": PROXMOX_PASS},
        verify=False,
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()["data"]
    return data["ticket"], data["CSRFPreventionToken"]


def api_get(ticket, csrf, path):
    r = requests.get(
        f"https://{PROXMOX_HOST}:{PROXMOX_PORT}/api2/json/{path}",
        cookies={"PVEAuthCookie": ticket},
        headers={"CSRFPreventionToken": csrf},
        verify=False,
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("data", [])


def api_post(ticket, csrf, path, data=None):
    r = requests.post(
        f"https://{PROXMOX_HOST}:{PROXMOX_PORT}/api2/json/{path}",
        cookies={"PVEAuthCookie": ticket},
        headers={"CSRFPreventionToken": csrf},
        json=data or {},
        verify=False,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def main():
    if not PROXMOX_PASS:
        print("ERROR: PROXMOX202_PASSWORD or PROXMOX_PASSWORD not set.")
        sys.exit(1)

    print("=" * 60)
    print("  PROXMOX: Clone Sandbox to Production")
    print(f"  Host: {PROXMOX_HOST}, Source VMID: {SOURCE_VMID}, Target: {TARGET_VMID}")
    print("=" * 60)

    ticket, csrf = get_ticket()
    print("Authenticated to Proxmox.")

    # Find node (usually pve)
    nodes = api_get(ticket, csrf, "nodes")
    node = nodes[0]["node"] if nodes else "pve"
    print(f"Using node: {node}")

    # Verify source VM exists
    vms = api_get(ticket, csrf, f"nodes/{node}/qemu")
    source = next((v for v in vms if v.get("vmid") == SOURCE_VMID), None)
    if not source:
        print(f"ERROR: Source VM {SOURCE_VMID} not found. Available VMs:")
        for v in vms:
            print(f"  VMID {v.get('vmid')}: {v.get('name')} ({v.get('status')})")
        sys.exit(1)
    print(f"Source VM: {source.get('name')} (status: {source.get('status')})")

    if any(v.get("vmid") == TARGET_VMID for v in vms):
        print(f"ERROR: Target VMID {TARGET_VMID} already exists. Remove it first or choose another ID.")
        sys.exit(1)

    # Clone (full clone)
    print(f"\nCloning VM {SOURCE_VMID} -> {TARGET_VMID} (name={TARGET_NAME})...")
    result = api_post(
        ticket,
        csrf,
        f"nodes/{node}/qemu/{SOURCE_VMID}/clone",
        {"newid": TARGET_VMID, "name": TARGET_NAME, "full": 1},
    )
    print(f"Clone task: {result.get('data')}")

    # Wait for clone to complete (poll until target VM exists)
    upid = result.get("data")
    if upid:
        print("Waiting for clone to finish (may take several minutes)...")
        for i in range(60):
            time.sleep(10)
            vms2 = api_get(ticket, csrf, f"nodes/{node}/qemu")
            if any(v.get("vmid") == TARGET_VMID for v in vms2):
                print("Clone completed successfully.")
                break
            print(f"  ... waiting ({i * 10}s)")
        else:
            print("Clone may still be in progress. Check Proxmox UI.")

    print("\n" + "=" * 60)
    print("  NEXT STEPS")
    print("=" * 60)
    print("1. Do NOT start both VMs on the same network (IP conflict).")
    print("2. Option A: Stop Sandbox, start clone, run reconfig script, reboot clone.")
    print("3. Option B: Run scripts/_reconfig_production_vm_186.py after starting clone.")
    print("4. See docs/MYCOSOFT_ORG_PRODUCTION_VM_CLONE_CI_CD_MAR13_2026.md")


if __name__ == "__main__":
    main()
