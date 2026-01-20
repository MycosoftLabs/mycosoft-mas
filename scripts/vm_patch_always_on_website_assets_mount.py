#!/usr/bin/env python3
"""Ensure the sandbox always-on website container mounts /opt/mycosoft/media/website/assets to /app/public/assets.

Fixes the common failure mode where `/assets/*` returns 404 on `sandbox.mycosoft.com` even though files exist on disk.
"""

from __future__ import annotations

import paramiko
import sys

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"

COMPOSE_PATH = "/home/mycosoft/mycosoft/mas/docker-compose.always-on.yml"

VOLUME_BLOCK = [
    "    volumes:\n",
    "    - /opt/mycosoft/media/website/assets:/app/public/assets:ro\n",
]


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

    if "/opt/mycosoft/media/website/assets:/app/public/assets:ro" in raw:
        print("[OK] assets mount already present in compose file.")
    else:
        lines = raw.splitlines(keepends=True)

        # Find the mycosoft-website service block
        try:
            start = next(i for i, line in enumerate(lines) if line.startswith("  mycosoft-website:"))
        except StopIteration:
            raise SystemExit("[ERROR] Could not find 'mycosoft-website:' in compose file.")

        # Insert volumes after `restart:` if present, otherwise right after the service header.
        insert_at = None
        for i in range(start, min(start + 120, len(lines))):
            if lines[i].startswith("    restart:"):
                insert_at = i + 1
                break
            # Stop if we hit another top-level service
            if i > start and lines[i].startswith("  ") and not lines[i].startswith("    "):
                break

        if insert_at is None:
            insert_at = start + 1

        # Avoid adding duplicate `volumes:` key if it exists (rare)
        has_volumes_key = any(
            lines[i].startswith("    volumes:") for i in range(start, min(start + 120, len(lines)))
        )
        if has_volumes_key:
            raise SystemExit("[ERROR] Found existing 'volumes:' under mycosoft-website, but no assets mount. Please patch manually.")

        updated = "".join(lines[:insert_at] + VOLUME_BLOCK + lines[insert_at:])
        with sftp.open(COMPOSE_PATH, "w") as f:
            f.write(updated.encode("utf-8"))
        print("[OK] Added assets mount to compose file.")

    # Recreate the website container so the new mount is applied
    print(
        run(
            ssh,
            "cd /home/mycosoft/mycosoft/mas && docker compose -p mycosoft-always-on -f docker-compose.always-on.yml up -d --no-deps --force-recreate mycosoft-website",
        )
    )

    # Quick origin check from inside the VM (bypass cloudflare)
    print(run(ssh, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/assets/mushroom1/a.mp4 || true"))

    ssh.close()


if __name__ == "__main__":
    main()

