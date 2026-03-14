#!/usr/bin/env python3
"""
Reconfigure cloned Production VM: IP 186, hostname, machine-id, stop cloudflared.
Phase 1 reconfig of mycosoft.org Production VM Clone CI/CD plan.
Date: March 13, 2026

Run this against the clone. If clone was started (Sandbox stopped), clone has IP 187.
  python _reconfig_production_vm_186.py --host 192.168.0.187
After reboot, VM will have IP 192.168.0.186.
"""
from __future__ import annotations

import argparse
import base64
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
for f in (REPO / ".credentials.local", REPO.parent / "website" / ".credentials.local"):
    if f.exists():
        for line in f.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import paramiko

VM_USER = "mycosoft"
VM_PASS = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
NEW_IP = "192.168.0.186"
NEW_HOSTNAME = "production-website"
GATEWAY = "192.168.0.1"
NETMASK = "255.255.255.0"


def run_sudo(ssh: paramiko.SSHClient, cmd: str, timeout: int = 60) -> tuple[str, str]:
    full = f"echo '{VM_PASS}' | sudo -S bash -c {repr(cmd)}"
    _, stdout, stderr = ssh.exec_command(full, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    return out, err


def main():
    parser = argparse.ArgumentParser(description="Reconfig Production VM clone")
    parser.add_argument(
        "--host",
        default="192.168.0.187",
        help="Current IP of clone (187 if Sandbox stopped and clone booted)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print commands only")
    args = parser.parse_args()

    if not VM_PASS and not args.dry_run:
        print("ERROR: VM_PASSWORD or VM_SSH_PASSWORD not set.")
        sys.exit(1)

    print("=" * 60)
    print("  Reconfig Production VM")
    print(f"  Target: {args.host} -> IP {NEW_IP}, hostname {NEW_HOSTNAME}")
    print("=" * 60)

    if args.dry_run:
        print("[DRY RUN - commands that would be executed]")
        print("1. Configure netplan for 192.168.0.186")
        print("2. hostnamectl set-hostname production-website")
        print("3. truncate machine-id, systemd-machine-id-setup")
        print("4. systemctl stop cloudflared && systemctl disable cloudflared")
        print("5. reboot")
        return

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(args.host, username=VM_USER, password=VM_PASS, timeout=30)
    print("Connected.")

    # Detect primary interface (has default route)
    _, stdout, _ = ssh.exec_command(
        "ip route show default 2>/dev/null | awk '{print $5}' | head -1"
    )
    raw = stdout.read().decode().strip()
    nic = (raw.split() or ["ens18"])[0] if raw else "ens18"
    if nic == "lo":
        nic = "ens18"
    print(f"Using interface: {nic}")

    netplan_conf = f"""network:
  version: 2
  ethernets:
    {nic}:
      addresses: [192.168.0.186/24]
      gateway4: 192.168.0.1
      nameservers:
        addresses: [1.1.1.1, 8.8.8.8]
"""
    run_sudo(ssh, "mkdir -p /etc/netplan")
    run_sudo(ssh, "rm -f /etc/netplan/*.yaml")
    b64 = base64.b64encode(netplan_conf.encode()).decode()
    run_sudo(ssh, f"echo {b64} | base64 -d > /etc/netplan/01-production.yaml")
    print("Netplan configured.")

    # Hostname
    run_sudo(ssh, f"hostnamectl set-hostname {NEW_HOSTNAME}")
    print("Hostname set.")

    # Machine ID
    run_sudo(ssh, "truncate -s 0 /etc/machine-id")
    run_sudo(ssh, "systemd-machine-id-setup")
    print("Machine ID reset.")

    # Stop cloudflared
    run_sudo(ssh, "systemctl stop cloudflared 2>/dev/null; systemctl disable cloudflared 2>/dev/null; true")
    print("Cloudflared stopped/disabled.")

    # Reboot
    print("Rebooting in 5 seconds...")
    run_sudo(ssh, "sleep 5 && reboot")
    ssh.close()

    print("\nVM rebooting. After ~60s, it should be at 192.168.0.186")
    print("Run scripts/_verify_production_vm_186.py to verify.")


if __name__ == "__main__":
    main()
