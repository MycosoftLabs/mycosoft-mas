#!/usr/bin/env python3
"""Rebuild container with updated code (5 device pages)."""

import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VM_HOST = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"
WEBSITE_PATH = "/home/mycosoft/mycosoft/website"
MAS_PATH = "/home/mycosoft/mycosoft/mas"
CONTAINER_NAME = "mycosoft-website"
NAS_MEDIA_PATH = "/opt/mycosoft/media/website/assets"


def run_cmd(client, cmd, timeout=600):
    print(f"  $ {cmd}")
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        if out:
            for line in out.split('\n')[-20:]:  # Show last 20 lines
                print(f"    {line}")
        if err and exit_code != 0:
            for line in err.split('\n')[:5]:
                print(f"    [ERR] {line}")
        return exit_code, out
    except Exception as e:
        print(f"    [ERROR] {e}")
        return -1, ""


def main():
    print("=" * 60)
    print("  REBUILD WITH 5 DEVICE PAGES")
    print("=" * 60)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VM_HOST, 22, VM_USER, VM_PASSWORD, 
                  timeout=30, look_for_keys=False, allow_agent=False)

    try:
        # Verify code has new pages
        print("\n[1] Verifying source code has Hyphae 1...")
        run_cmd(client, f"ls -la {WEBSITE_PATH}/components/devices/ | grep hyphae")
        run_cmd(client, f"cat {WEBSITE_PATH}/components/devices/hyphae1-details.tsx | head -5")

        # Stop container
        print("\n[2] Stopping container...")
        run_cmd(client, f"docker stop {CONTAINER_NAME} || true")
        run_cmd(client, f"docker rm {CONTAINER_NAME} || true")

        # Clean Docker cache
        print("\n[3] Cleaning Docker cache...")
        run_cmd(client, "docker system prune -f")
        run_cmd(client, "docker builder prune -f")
        
        # Remove old images
        print("\n[4] Removing old images...")
        run_cmd(client, "docker images | grep mycosoft-website | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true")

        # Rebuild
        print("\n[5] Rebuilding Docker image (3-5 minutes)...")
        exit_code, out = run_cmd(client, 
            f"cd {MAS_PATH} && docker compose -f docker-compose.always-on.yml build {CONTAINER_NAME} --no-cache 2>&1 | tail -30",
            timeout=600)

        # Start with NAS mount
        print("\n[6] Starting container with NAS mount...")
        run_cmd(client, f"""docker run -d \
            --name {CONTAINER_NAME} \
            -p 3000:3000 \
            -v {NAS_MEDIA_PATH}:/app/public/assets:ro \
            --network mycosoft-network \
            --restart unless-stopped \
            mycosoft-always-on-mycosoft-website:latest""")

        print("\n[7] Waiting for startup (30s)...")
        time.sleep(30)

        # Verify
        print("\n[8] Verifying all 5 device pages...")
        devices = ["mushroom-1", "sporebase", "hyphae-1", "myconode", "alarm"]
        for device in devices:
            exit_code, out = run_cmd(client, 
                f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:3000/devices/{device}")
            status = "OK" if "200" in out else "FAIL"
            print(f"      /devices/{device}: {status}")

        print("\n" + "=" * 60)
        print("  REBUILD COMPLETE - Purge Cloudflare and test")
        print("=" * 60)

    finally:
        client.close()


if __name__ == "__main__":
    main()
