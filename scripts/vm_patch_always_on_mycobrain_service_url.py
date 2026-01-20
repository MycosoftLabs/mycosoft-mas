#!/usr/bin/env python3
"""Patch sandbox always-on compose to point MYCOBRAIN_SERVICE_URL at the Windows-hosted MycoBrain service.

This resolves the common mismatch where Cloudflare tunnels terminate on the VM but MycoBrain runs on a Windows host.
"""

from __future__ import annotations

import paramiko
import sys

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"

COMPOSE_PATH = "/home/mycosoft/mycosoft/mas/docker-compose.always-on.yml"

# Windows host running MycoBrain on LAN (update if your Windows IP changes)
WINDOWS_MYCORBRAIN_URL = "http://192.168.0.172:8003"


def run(ssh: paramiko.SSHClient, cmd: str) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return (out + ("\n" + err if err.strip() else "")).strip()


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)

    sftp = ssh.open_sftp()
    with sftp.open(COMPOSE_PATH, "r") as f:
        raw = f.read().decode("utf-8", errors="replace")

    old_variants = [
        "MYCOBRAIN_SERVICE_URL: http://host.docker.internal:8003",
        "MYCOBRAIN_SERVICE_URL: http://192.168.0.172:8003",
    ]
    new_line = f"      MYCOBRAIN_SERVICE_URL: {WINDOWS_MYCORBRAIN_URL}"

    updated = raw
    replaced = False
    for old in old_variants:
        if old in updated:
            updated = updated.replace(old, new_line)
            replaced = True
            break

    if not replaced:
        raise SystemExit("[ERROR] Could not find MYCOBRAIN_SERVICE_URL line to patch.")

    if updated != raw:
        with sftp.open(COMPOSE_PATH, "w") as f:
            f.write(updated.encode("utf-8"))
        print("[OK] Patched MYCOBRAIN_SERVICE_URL in compose file.")
    else:
        print("[OK] MYCOBRAIN_SERVICE_URL already correct.")

    # Recreate website container so env changes apply
    print(
        run(
            ssh,
            "cd /home/mycosoft/mycosoft/mas && docker compose -p mycosoft-always-on -f docker-compose.always-on.yml up -d --no-deps --force-recreate mycosoft-website",
        )
    )

    # Quick internal connectivity check from within the VM (LAN reachability)
    print(run(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' {WINDOWS_MYCORBRAIN_URL}/health || true"))

    ssh.close()


if __name__ == "__main__":
    main()

