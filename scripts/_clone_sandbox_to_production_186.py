#!/usr/bin/env python3
"""Clone Sandbox VM (103) to Production VM 186 on Proxmox.

Uses vzdump + qmrestore (avoids qm clone EFI disk size mismatch on local-lvm).
Creates mycosoft-production (VMID 186). Requires: PROXMOX202_PASSWORD or PROXMOX_PASSWORD
or VM_PASSWORD in .credentials.local.

Backup storage: Set BACKUP_STORAGE=nas-backup (or --storage nas-backup) to write
vzdump to NAS NFS instead of local disk (avoids "No space left" on Proxmox 202).
See docs/R720_AND_BACKUP_TO_NAS_MAR13_2026.md.

Date: March 13, 2026
"""
import argparse
import os
import re
import sys
import time
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


def run(ssh, cmd, timeout=600):
    print(f"Running: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    if out:
        print(out)
    if err:
        print(err, file=sys.stderr)
    return code, out, err


def main():
    ap = argparse.ArgumentParser(description="Clone Sandbox VM 103 to Production VM 186 on Proxmox")
    ap.add_argument(
        "--storage",
        default=os.environ.get("BACKUP_STORAGE", "local"),
        help="Proxmox storage for vzdump (default: local). Use nas-backup for NAS NFS.",
    )
    args = ap.parse_args()
    storage = args.storage

    if not PROXMOX_PASS:
        print("ERROR: PROXMOX202_PASSWORD, PROXMOX_PASSWORD, or VM_PASSWORD required.")
        sys.exit(1)
    print(f"Connecting to Proxmox {PROXMOX_HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(PROXMOX_HOST, username=PROXMOX_USER, password=PROXMOX_PASS, timeout=15)
    except Exception as e:
        print(f"ERROR: Proxmox SSH failed: {e}")
        sys.exit(1)
    try:
        # 1. Remove VM 186 if it exists (from prior failed attempts)
        run(ssh, "qm destroy 186 --purge 1", timeout=60)
        time.sleep(2)

        # 2. Backup VM 103 (snapshot mode, compressed)
        dump_dir = "/var/lib/vz/dump" if storage == "local" else f"/mnt/pve/{storage}/dump"
        code, out, _ = run(
            ssh, f"vzdump 103 --mode snapshot --compress zstd --storage {storage}", timeout=3600
        )
        if code != 0:
            print("ERROR: vzdump failed")
            sys.exit(1)
        # Find the backup file (vzdump-qemu-103-YYYYMMDD-HHMMSS.vma.zst)
        code2, list_out, _ = run(
            ssh, f"ls -t {dump_dir}/vzdump-qemu-103-*.vma.zst 2>/dev/null | head -1", timeout=10
        )
        match = re.search(r"(" + re.escape(dump_dir) + r"/vzdump-qemu-103-[^\s]+)", list_out)
        if not match:
            print("ERROR: Could not find backup file")
            sys.exit(1)
        backup_path = match.group(1).strip()
        print(f"Backup: {backup_path}")

        # 3. Restore as VM 186
        code, out, err = run(ssh, f"qmrestore {backup_path} 186", timeout=3600)
        if code != 0:
            print("ERROR: qmrestore failed")
            sys.exit(1)

        # 4. Set name
        run(ssh, "qm set 186 --name mycosoft-production", timeout=30)

        # 5. Remove backup to free space (only when on local - NAS has plenty)
        if storage == "local":
            run(ssh, f"rm -f {backup_path}", timeout=10)
        else:
            print(f"Backup left on {storage} (nas-backup/NFS has plenty of space)")

        print("Clone complete. VM 186 (mycosoft-production) created.")
        print("Next: Reconfigure for 192.168.0.186, then start VM and enable SSH.")
    finally:
        ssh.close()


if __name__ == "__main__":
    main()
