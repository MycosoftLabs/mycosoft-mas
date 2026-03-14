#!/usr/bin/env python3
"""
Verify Production VM (192.168.0.186): ping, SSH, Docker, curl localhost:3000, NAS mount.
Phase 1 verify of mycosoft.org Production VM Clone CI/CD plan.
Date: March 13, 2026
"""
from __future__ import annotations

import os
import subprocess
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

VM_HOST = "192.168.0.186"
VM_USER = "mycosoft"
VM_PASS = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")


def main():
    print("=" * 60)
    print("  Verify Production VM (186)")
    print("=" * 60)

    all_ok = True

    # 1. Ping
    print("\n1. Ping 192.168.0.186...")
    r = subprocess.run(
        ["ping", "-n", "2", VM_HOST] if sys.platform == "win32" else ["ping", "-c", "2", VM_HOST],
        capture_output=True,
        timeout=10,
    )
    if r.returncode == 0:
        print("   OK")
    else:
        print("   FAIL")
        all_ok = False

    # 2. SSH
    print("\n2. SSH...")
    if not VM_PASS:
        print("   SKIP (VM_PASSWORD not set)")
    else:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=15)
            ssh.close()
            print("   OK")
        except Exception as e:
            print(f"   FAIL: {e}")
            all_ok = False

    # 3–5. Remote checks via SSH
    if VM_PASS and all_ok:
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=15)

            # 3. Docker
            _, out, err = ssh.exec_command("docker ps --filter name=mycosoft-website --format '{{.Names}}'", timeout=10)
            names = out.read().decode().strip()
            if "mycosoft-website" in names:
                print("\n3. Docker (mycosoft-website)... OK")
            else:
                print("\n3. Docker (mycosoft-website)... FAIL (container not running)")
                all_ok = False

            # 4. Local curl 200
            _, out, _ = ssh.exec_command(
                "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000",
                timeout=10,
            )
            code = out.read().decode().strip()
            if code == "200":
                print("4. Local curl localhost:3000... OK (200)")
            else:
                print(f"4. Local curl localhost:3000... FAIL (HTTP {code})")
                all_ok = False

            # 5. NAS mount
            _, out, _ = ssh.exec_command(
                "test -d /opt/mycosoft/media/website/assets && echo OK || echo MISSING",
                timeout=5,
            )
            m = out.read().decode().strip()
            if m == "OK":
                print("5. NAS mount (/opt/mycosoft/media/website/assets)... OK")
            else:
                print("5. NAS mount... FAIL (path missing or not mounted)")
                all_ok = False

            ssh.close()
        except Exception as e:
            print(f"\n   SSH checks failed: {e}")
            all_ok = False
    else:
        print("\n3–5. Skipped (SSH failed or no password)")

    print("\n" + "=" * 60)
    if all_ok:
        print("  All checks passed.")
    else:
        print("  Some checks failed.")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
