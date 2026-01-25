#!/usr/bin/env python3
"""Start container with network."""

import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VM_HOST = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"
CONTAINER_NAME = "mycosoft-website"
NAS_MEDIA_PATH = "/opt/mycosoft/media/website/assets"


def run_cmd(client, cmd, timeout=60):
    print(f"  $ {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if out:
        for line in out.split('\n')[:10]:
            print(f"    {line}")
    if err:
        for line in err.split('\n')[:3]:
            print(f"    [!] {line}")
    return out


def main():
    print("=" * 60)
    print("  START CONTAINER")
    print("=" * 60)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VM_HOST, 22, VM_USER, VM_PASSWORD, 
                  timeout=30, look_for_keys=False, allow_agent=False)

    try:
        # Remove any failed container
        print("\n[1] Cleaning up...")
        run_cmd(client, f"docker rm -f {CONTAINER_NAME} 2>/dev/null || true")

        # Create network
        print("\n[2] Creating network...")
        run_cmd(client, "docker network create mycosoft-network 2>/dev/null || true")

        # Start container
        print("\n[3] Starting container...")
        run_cmd(client, f"""docker run -d \
            --name {CONTAINER_NAME} \
            -p 3000:3000 \
            -v {NAS_MEDIA_PATH}:/app/public/assets:ro \
            --network mycosoft-network \
            --restart unless-stopped \
            mycosoft-always-on-mycosoft-website:latest""")

        print("\n[4] Waiting for startup (25s)...")
        time.sleep(25)

        # Verify container
        print("\n[5] Container status...")
        run_cmd(client, f"docker ps --filter name={CONTAINER_NAME}")

        # Test endpoints
        print("\n[6] Testing all 5 device pages...")
        devices = ["mushroom-1", "sporebase", "hyphae-1", "myconode", "alarm"]
        all_ok = True
        for device in devices:
            out = run_cmd(client, f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:3000/devices/{device}")
            status = "OK" if "200" in out else "FAIL"
            if "200" not in out:
                all_ok = False
            print(f"      /devices/{device}: {status}")

        if all_ok:
            print("\n[7] All 5 device pages working!")
        else:
            print("\n[7] Some pages failed - checking logs...")
            run_cmd(client, f"docker logs {CONTAINER_NAME} 2>&1 | tail -10")

        print("\n" + "=" * 60)
        print("  DONE - Purge Cloudflare and hard refresh browser")
        print("=" * 60)

    finally:
        client.close()


if __name__ == "__main__":
    main()
