#!/usr/bin/env python3
"""
Apply VM docker-compose media mount for website container.

Edits: /opt/mycosoft/docker-compose.yml
Adds (if missing) a read-only volume mount so:
  /opt/mycosoft/media/website/assets  ->  /app/public/assets

Then restarts only the website service.

This makes video updates instant (sync files only; no docker rebuild).
"""

from __future__ import annotations

import re
import sys

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


VM_HOST = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"

COMPOSE_PATH = "/opt/mycosoft/docker-compose.yml"
HOST_MEDIA_ASSETS = "/opt/mycosoft/media/website/assets"
CONTAINER_PUBLIC_ASSETS = "/app/public/assets"

SERVICE_NAME = "mycosoft-website"
PROJECT_NAME = "mycosoft-production"


def exec_cmd(ssh: paramiko.SSHClient, cmd: str, timeout: int = 120) -> tuple[int, str, str]:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return code, out, err



def main() -> int:
    mount_line = f"{HOST_MEDIA_ASSETS}:{CONTAINER_PUBLIC_ASSETS}:ro"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

    try:
        # Ensure media directory exists
        code, out, err = exec_cmd(
            ssh,
            f"mkdir -p {HOST_MEDIA_ASSETS}",
            timeout=120,
        )
        if code != 0:
            print("[ERROR] Failed to ensure media directory exists")
            print(err)
            return 1

        # Read compose
        code, compose, err = exec_cmd(ssh, f"cat {COMPOSE_PATH}", timeout=60)
        if code != 0 or not compose.strip():
            print(f"[ERROR] Could not read {COMPOSE_PATH}")
            print(err)
            return 1

        if mount_line in compose:
            print("[OK] Media mount already present in compose.")
        else:
            print("[INFO] Injecting media volume mount into compose...")

            # Naive but safe-ish insertion:
            # Find the service block for mycosoft-website, then add under `volumes:` if present,
            # else add a new `volumes:` section right after `container_name:` or `image:` line.
            # This assumes docker-compose.yml uses 2-space indentation under services.
            pattern = rf"(^\s+{re.escape(SERVICE_NAME)}:\s*$)([\s\S]*?)(^\s+\S)"
            m = re.search(pattern, compose, flags=re.MULTILINE)
            if not m:
                print(f"[ERROR] Could not locate service '{SERVICE_NAME}' in compose.")
                return 1

            service_start = m.start(1)
            service_end = m.start(3)
            service_block = compose[service_start:service_end]

            if re.search(r"^\s+volumes:\s*$", service_block, flags=re.MULTILINE):
                # Insert right after volumes:
                service_block_new = re.sub(
                    r"(^\s+volumes:\s*$)",
                    r"\1\n      - " + mount_line,
                    service_block,
                    count=1,
                    flags=re.MULTILINE,
                )
            else:
                # Insert a new volumes section after container_name or image if found, else after service header.
                insert_after = None
                for key in ("container_name:", "image:", "build:"):
                    mm = re.search(rf"(^\s+{re.escape(key)}.*$)", service_block, flags=re.MULTILINE)
                    if mm:
                        insert_after = mm.group(1)
                        break

                if insert_after:
                    service_block_new = service_block.replace(
                        insert_after,
                        insert_after + "\n    volumes:\n      - " + mount_line,
                        1,
                    )
                else:
                    # fallback: right after service header line
                    service_lines = service_block.splitlines(True)
                    service_block_new = (
                        service_lines[0] + "    volumes:\n      - " + mount_line + "\n" + "".join(service_lines[1:])
                    )

            new_compose = compose[:service_start] + service_block_new + compose[service_end:]

            # Write back via heredoc
            # Use sudo tee to preserve permissions.
            safe = new_compose.replace("\\", "\\\\").replace("$", "\\$")
            cmd = f"tee {COMPOSE_PATH} >/dev/null <<'EOF'\n{safe}\nEOF\n"
            code, out, err = exec_cmd(ssh, cmd, timeout=120)
            if code != 0:
                print("[ERROR] Failed writing compose.")
                print(err)
                return 1

            print("[OK] Compose updated.")

        # Restart website only
        print("[INFO] Restarting website container (no rebuild)...")
        code, out, err = exec_cmd(
            ssh,
            f"cd /opt/mycosoft && docker compose -p {PROJECT_NAME} up -d {SERVICE_NAME}",
            timeout=300,
        )
        if code != 0:
            combined = (out + "\n" + err).strip()
            if "container name" in combined.lower() and "already in use" in combined.lower():
                print("[WARN] Container name conflict detected. Removing existing container and retrying...")
                exec_cmd(ssh, f"docker rm -f {SERVICE_NAME} >/dev/null 2>&1 || true", timeout=60)
                code, out, err = exec_cmd(
                    ssh,
                    f"cd /opt/mycosoft && docker compose -p {PROJECT_NAME} up -d {SERVICE_NAME}",
                    timeout=300,
                )
                if code != 0:
                    print("[ERROR] Failed to restart website after removing existing container.")
                    print(out)
                    print(err)
                    return 1
            else:
                print("[ERROR] Failed to restart website.")
                print(out)
                print(err)
                return 1

        # Quick verification: the video URLs should return 200 if files exist.
        print("[INFO] Verifying media files serve from website...")
        checks = [
            "/assets/mushroom1/waterfall%201.mp4",
            "/assets/mushroom1/mushroom%201%20walking.mp4",
        ]
        for path in checks:
            code, out, err = exec_cmd(
                ssh,
                f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:3000{path}",
                timeout=30,
            )
            status = out.strip()
            print(f"[CHECK] {path} -> {status}")

        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())

