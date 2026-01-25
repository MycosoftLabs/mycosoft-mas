#!/usr/bin/env python3
"""
Deploy Website via SSH - Direct connection to VM 103
Uses SSH instead of Proxmox API for more reliable connections.
"""

import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# VM Configuration
VM_HOST = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"
VM_PORT = 22

# Paths
WEBSITE_PATH = "/home/mycosoft/mycosoft/website"
MAS_PATH = "/home/mycosoft/mycosoft/mas"
COMPOSE_FILE = "docker-compose.always-on.yml"
CONTAINER_NAME = "mycosoft-website"
NAS_MEDIA_PATH = "/opt/mycosoft/media/website/assets"


def run_ssh_command(client, cmd, timeout=300):
    """Run a command via SSH and return output."""
    print(f"  $ {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if out:
        for line in out.split('\n')[:20]:  # Limit output
            print(f"    {line}")
    if err and exit_code != 0:
        for line in err.split('\n')[:10]:
            print(f"    [ERR] {line}")
    return exit_code, out, err


def main():
    print("=" * 70)
    print("  MYCOSOFT WEBSITE DEPLOYMENT VIA SSH")
    print("=" * 70)
    print()

    # Connect via SSH
    print("[1] Connecting to VM via SSH...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(
            hostname=VM_HOST,
            port=VM_PORT,
            username=VM_USER,
            password=VM_PASSWORD,
            timeout=30,
            look_for_keys=False,
            allow_agent=False
        )
        print(f"    Connected to {VM_USER}@{VM_HOST}")
    except Exception as e:
        print(f"    [ERROR] Cannot connect: {e}")
        return 1

    try:
        # Step 2: Pull latest code
        print()
        print("[2] Pulling latest code from GitHub...")
        run_ssh_command(client, f"cd {WEBSITE_PATH} && git fetch origin main")
        run_ssh_command(client, f"cd {WEBSITE_PATH} && git reset --hard origin/main")
        exit_code, out, _ = run_ssh_command(client, f"cd {WEBSITE_PATH} && git log -1 --oneline")
        print(f"    Latest commit: {out}")

        # Step 3: Stop container
        print()
        print("[3] Stopping current container...")
        run_ssh_command(client, f"docker stop {CONTAINER_NAME} || true")
        run_ssh_command(client, f"docker rm {CONTAINER_NAME} || true")

        # Step 4: Clean Docker cache
        print()
        print("[4] Cleaning Docker caches...")
        run_ssh_command(client, "docker system prune -f")
        run_ssh_command(client, "docker builder prune -f")

        # Step 5: Clean Next.js cache
        print()
        print("[5] Cleaning Next.js cache...")
        run_ssh_command(client, f"rm -rf {WEBSITE_PATH}/.next/cache || true")

        # Step 6: Build new image
        print()
        print("[6] Building Docker image (this may take 3-5 minutes)...")
        exit_code, out, err = run_ssh_command(
            client, 
            f"cd {MAS_PATH} && docker compose -f {COMPOSE_FILE} build {CONTAINER_NAME} --no-cache 2>&1 | tail -30",
            timeout=600
        )
        if exit_code != 0:
            print("    [WARN] Build may have issues, continuing...")

        # Step 7: Start container with NAS mount
        print()
        print("[7] Starting container with NAS mount...")
        run_cmd = f"""docker run -d \\
            --name {CONTAINER_NAME} \\
            -p 3000:3000 \\
            -v {WEBSITE_PATH}:/app \\
            -v {NAS_MEDIA_PATH}:/app/public/assets:ro \\
            --network mycosoft-network \\
            mycosoft-always-on-mycosoft-website:latest"""
        exit_code, out, err = run_ssh_command(client, run_cmd)
        
        if exit_code != 0:
            print("    [WARN] Direct run failed, trying docker compose...")
            run_ssh_command(
                client,
                f"cd {MAS_PATH} && docker compose -f {COMPOSE_FILE} up -d {CONTAINER_NAME}"
            )

        # Step 8: Wait for startup
        print()
        print("[8] Waiting for container to start (30s)...")
        time.sleep(30)

        # Step 9: Verify container
        print()
        print("[9] Verifying container status...")
        run_ssh_command(client, f"docker ps --filter name={CONTAINER_NAME}")
        
        # Step 10: Test endpoints
        print()
        print("[10] Testing endpoints...")
        run_ssh_command(client, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/ || echo 'FAIL'")
        run_ssh_command(client, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/devices || echo 'FAIL'")
        run_ssh_command(client, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/devices/sporebase || echo 'FAIL'")

        # Step 11: Check for new content
        print()
        print("[11] Checking for new device pages...")
        run_ssh_command(client, "curl -s http://localhost:3000/devices/sporebase | grep -c 'SporeBase' || echo '0'")
        run_ssh_command(client, "curl -s http://localhost:3000/devices/hyphae-1 | grep -c 'Hyphae' || echo '0'")
        run_ssh_command(client, "curl -s http://localhost:3000/devices/myconode | grep -c 'MycoNode' || echo '0'")
        run_ssh_command(client, "curl -s http://localhost:3000/devices/alarm | grep -c 'ALARM' || echo '0'")

        print()
        print("=" * 70)
        print("  DEPLOYMENT COMPLETE")
        print("=" * 70)
        print()
        print("  Next steps:")
        print("    1. Purge Cloudflare cache (dashboard -> Caching -> Purge Everything)")
        print("    2. Hard refresh browser (Ctrl+Shift+R)")
        print("    3. Test: https://sandbox.mycosoft.com/devices")
        print()
        
        return 0

    finally:
        client.close()
        print("  SSH connection closed.")


if __name__ == "__main__":
    sys.exit(main())
