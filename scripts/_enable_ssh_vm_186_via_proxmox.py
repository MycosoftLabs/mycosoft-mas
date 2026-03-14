#!/usr/bin/env python3
"""Enable SSH on VM 186 via Proxmox host (qm guest exec).

VM 186 is pingable but SSH port 22 unreachable. This script SSHs to the Proxmox
host (192.168.0.202) and runs systemctl start ssh inside the VM via qemu-guest-agent.

Requires: Proxmox host must be reachable; VM 186 must have qemu-guest-agent installed.
If qemu-guest-agent is not installed, use Proxmox web console:
  1. Open https://192.168.0.202:8006
  2. Select VM 186 -> Console
  3. Login (mycosoft / VM_PASSWORD)
  4. Run: sudo systemctl enable ssh && sudo systemctl start ssh

Date: March 13, 2026
"""

import os
import sys
from pathlib import Path

import paramiko

REPO = Path(__file__).resolve().parent.parent
for f in (REPO / ".credentials.local", REPO.parent / "website" / ".credentials.local"):
    if f.exists():
        for line in f.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))

PROXMOX_HOST = "192.168.0.202"
PROXMOX_USER = "root"
PROXMOX_PASS = (
    os.environ.get("PROXMOX202_PASSWORD")
    or os.environ.get("PROXMOX_PASSWORD")
    or os.environ.get("VM_PASSWORD")
    or os.environ.get("VM_SSH_PASSWORD")
)
VMID = 186


def main():
    if not PROXMOX_PASS:
        print("ERROR: PROXMOX202_PASSWORD, PROXMOX_PASSWORD, or VM_PASSWORD required.")
        sys.exit(1)

    print(f"Connecting to Proxmox host {PROXMOX_HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(PROXMOX_HOST, username=PROXMOX_USER, password=PROXMOX_PASS, timeout=15)
    except Exception as e:
        print(f"ERROR: Proxmox SSH failed: {e}")
        print(f"  Ensure {PROXMOX_HOST} is reachable and PROXMOX202_PASSWORD/PROXMOX_PASSWORD is set.")
        sys.exit(1)

    # Enable and start SSH in VM 186 via qemu-guest-agent
    guest_cmd = "systemctl enable ssh && systemctl start ssh"
    cmd = f"qm guest exec {VMID} -- sh -c {repr(guest_cmd)}"
    print(f"Running: qm guest exec {VMID} -- {guest_cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()

    if code == 0:
        print("SSH enabled and started on VM 186.")
        print("Wait ~5s, then run: python scripts/_preflight_production_live.py")
    else:
        print(f"qm guest exec failed (exit {code}): {err or out}")
        # List VMs to help identify Production if 186 doesn't exist
        stdin2, stdout2, stderr2 = ssh.exec_command("qm list 2>/dev/null || pvesh get /cluster/resources --type vm 2>/dev/null", timeout=10)
        vm_list = (stdout2.read() + stderr2.read()).decode(errors="replace").strip()
        if vm_list:
            print("\nVMs on Proxmox (find Production / 192.168.0.186):")
            for line in vm_list.splitlines()[:20]:
                print(f"  {line}")
        print("\nFallback: Use Proxmox web console:")
        print(f"  1. Open https://{PROXMOX_HOST}:8006")
        print(f"  2. Select the Production VM (VMID {VMID} or the VM with IP 192.168.0.186) -> Console")
        print("  3. Login (mycosoft / VM_PASSWORD) and run: sudo systemctl enable ssh && sudo systemctl start ssh")
        sys.exit(1)

    ssh.close()


if __name__ == "__main__":
    main()
