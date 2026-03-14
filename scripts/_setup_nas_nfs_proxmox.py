#!/usr/bin/env python3
"""Configure NFS storage on Proxmox 202 for NAS (192.168.0.105). Runs all steps via SSH."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko


def load_creds() -> str:
    creds = Path(__file__).resolve().parents[1] / ".credentials.local"
    pw = os.environ.get("PROXMOX202_PASSWORD", "")
    if creds.exists():
        for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == "PROXMOX202_PASSWORD" and v.strip():
                pw = v.strip()
                break
    return pw


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 30) -> tuple[int, str, str]:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    return code, out.strip(), err.strip()


def main() -> int:
    pw = load_creds()
    if not pw:
        print("ERROR: PROXMOX202_PASSWORD not in .credentials.local or env")
        return 1

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.202", username="root", password=pw, timeout=15)
    try:
        # 1. Scan NFS server
        print("=== pvesm scan nfs 192.168.0.105 ===")
        code, out, err = run(ssh, "pvesm scan nfs 192.168.0.105")
        print(out or "(empty)")
        if err:
            print("stderr:", err)

        # 2. showmount for reference
        print("\n=== showmount -e 192.168.0.105 ===")
        code2, out2, err2 = run(ssh, "showmount -e 192.168.0.105")
        print(out2 or "(empty)")
        if err2:
            print("stderr:", err2)

        # 3. Try adding NFS storage with UniFi path (share or mycosoft.com)
        # UniFi format: /var/nfs/shared/<ShareName>
        for export in ["/var/nfs/shared/share", "/var/nfs/shared/mycosoft.com"]:
            print(f"\n=== Adding NFS storage: {export} ===")
            cmd = (
                f"pvesm add nfs nas-backup --server 192.168.0.105 --export {export} "
                "--content backup --options vers=3,soft 2>&1"
            )
            code3, out3, err3 = run(ssh, cmd)
            combined = (out3 + "\n" + err3).strip()
            try:
                print(combined)
            except UnicodeEncodeError:
                print(combined.encode("ascii", "replace").decode("ascii"))
            if code3 == 0:
                print("\nSUCCESS: nas-backup storage added")
                return 0
            if "already exists" in combined.lower():
                print("\nStorage nas-backup already exists")
                return 0

        # 4. List current storage
        print("\n=== pvesm status ===")
        code4, out4, _ = run(ssh, "pvesm status")
        print(out4)

        return 1 if code3 != 0 else 0
    finally:
        ssh.close()


if __name__ == "__main__":
    sys.exit(main())
