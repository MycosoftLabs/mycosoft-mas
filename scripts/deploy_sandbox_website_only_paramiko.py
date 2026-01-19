#!/usr/bin/env python3
"""
Deploy ONLY the Mycosoft Website to Sandbox VM (Paramiko)
========================================================

This targets the *main* sandbox compose on the VM:
  /opt/mycosoft/docker-compose.yml

    It does:
1) git pull/reset website repo at /opt/mycosoft/website
2) docker build -t website-website:latest --no-cache . (from /opt/mycosoft/website)
3) docker compose up -d --force-recreate mycosoft-website (project mycosoft-production)
4) restarts cloudflared (optional; requires sudoless systemctl or configured separately)
5) verifies origin endpoints (localhost:3000) and key media assets

Note: Cloudflare cache purge is still required after rebuild (Purge Everything).
"""

from __future__ import annotations

import sys
import time

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


VM_HOST = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"

WEBSITE_REPO = "/opt/mycosoft/website"
COMPOSE_ROOT = "/opt/mycosoft"
PROJECT_NAME = "mycosoft-production"
SERVICE_NAME = "mycosoft-website"
IMAGE_TAG = "website-website:latest"


def run(ssh: paramiko.SSHClient, cmd: str, *, timeout: int = 1200) -> int:
    print("\n" + "=" * 60)
    print(cmd)
    print("=" * 60)
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)

    # Stream output so it doesn't look "stuck"
    start = time.time()
    while not stdout.channel.exit_status_ready():
        if stdout.channel.recv_ready():
            chunk = stdout.channel.recv(4096).decode("utf-8", errors="replace")
            if chunk:
                print(chunk, end="")
        if stderr.channel.recv_stderr_ready():
            chunk = stderr.channel.recv_stderr(4096).decode("utf-8", errors="replace")
            if chunk:
                print(chunk, end="")
        if time.time() - start > timeout:
            raise TimeoutError(f"Command timed out after {timeout}s")
        time.sleep(0.2)

    # Drain remaining
    while stdout.channel.recv_ready():
        print(stdout.channel.recv(4096).decode("utf-8", errors="replace"), end="")
    while stderr.channel.recv_stderr_ready():
        print(stderr.channel.recv_stderr(4096).decode("utf-8", errors="replace"), end="")

    return stdout.channel.recv_exit_status()


def main() -> int:
    print("MYCOSOFT SANDBOX WEBSITE DEPLOY (website only)")
    print(f"Target: {VM_HOST}")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

    try:
        code = run(ssh, "free -h && uptime", timeout=60)
        if code != 0:
            return code

        code = run(ssh, f"cd {WEBSITE_REPO} && git fetch origin && git reset --hard origin/main && git rev-parse --short HEAD", timeout=120)
        if code != 0:
            return code

        # Build website image (no cache) using the website repo as context
        code = run(
            ssh,
            f"cd {WEBSITE_REPO} && docker build -t {IMAGE_TAG} --no-cache .",
            timeout=5400,
        )
        if code != 0:
            return code

        # Restart container
        code = run(
            ssh,
            f"cd {COMPOSE_ROOT} && docker compose -p {PROJECT_NAME} up -d --no-deps --force-recreate {SERVICE_NAME}",
            timeout=600,
        )
        if code != 0:
            return code

        # Verify origin
        run(ssh, "docker ps --filter name=mycosoft-website --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'", timeout=60)
        run(ssh, "curl -s -I http://localhost:3000/ | head -15", timeout=60)
        run(ssh, "curl -s -I 'http://localhost:3000/assets/mushroom1/waterfall%201.mp4' | head -15", timeout=60)
        run(ssh, "curl -s -I 'http://localhost:3000/assets/mushroom1/mushroom%201%20walking.mp4' | head -15", timeout=60)

        print("\nDONE.")
        print("Next manual step: Cloudflare → Purge Everything, then hard refresh.")
        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())

