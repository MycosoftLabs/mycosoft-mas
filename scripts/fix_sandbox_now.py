#!/usr/bin/env python3
"""
Emergency fix for sandbox - NAS mount timeout and 502 error
"""

import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VM_HOST = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"
VM_PORT = 22

WEBSITE_PATH = "/home/mycosoft/mycosoft/website"
MAS_PATH = "/home/mycosoft/mycosoft/mas"
CONTAINER_NAME = "mycosoft-website"


def run_cmd(client, cmd, timeout=120):
    """Run command and print output."""
    print(f"  $ {cmd}")
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        if out:
            for line in out.split('\n')[:15]:
                print(f"    {line}")
        if err and exit_code != 0:
            for line in err.split('\n')[:5]:
                print(f"    [ERR] {line}")
        return exit_code, out
    except Exception as e:
        print(f"    [TIMEOUT/ERROR] {e}")
        return -1, ""


def main():
    print("=" * 60)
    print("  EMERGENCY SANDBOX FIX")
    print("=" * 60)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("\n[1] Connecting to VM...")
        client.connect(VM_HOST, VM_PORT, VM_USER, VM_PASSWORD, 
                      timeout=30, look_for_keys=False, allow_agent=False)
        print("    Connected!")

        # Check NAS mount status
        print("\n[2] Checking NAS mount status...")
        run_cmd(client, "mount | grep 192.168.0.105 || echo 'No NAS mount found'")
        run_cmd(client, "ls -la /opt/mycosoft/media/website/assets/ 2>&1 | head -5 || echo 'Cannot access NAS'")

        # Check what's blocking
        print("\n[3] Checking for stuck processes...")
        run_cmd(client, "ps aux | grep -E 'mount|cifs' | head -5")

        # Fix git permissions
        print("\n[4] Fixing git repository permissions...")
        run_cmd(client, f"sudo chown -R mycosoft:mycosoft {WEBSITE_PATH}/.git")
        run_cmd(client, f"sudo chmod -R 755 {WEBSITE_PATH}/.git")

        # Pull latest code
        print("\n[5] Pulling latest code...")
        run_cmd(client, f"cd {WEBSITE_PATH} && git fetch origin main 2>&1")
        run_cmd(client, f"cd {WEBSITE_PATH} && git reset --hard origin/main 2>&1")
        run_cmd(client, f"cd {WEBSITE_PATH} && git log -1 --oneline")

        # Stop any existing containers
        print("\n[6] Stopping containers...")
        run_cmd(client, f"docker stop {CONTAINER_NAME} 2>/dev/null || true")
        run_cmd(client, f"docker rm {CONTAINER_NAME} 2>/dev/null || true")

        # Create network if missing
        print("\n[7] Creating docker network if missing...")
        run_cmd(client, "docker network create mycosoft-network 2>/dev/null || true")

        # Check if NAS is accessible, if not skip volume mount
        print("\n[8] Testing NAS accessibility...")
        exit_code, out = run_cmd(client, "timeout 5 ls /opt/mycosoft/media/website/assets/ 2>&1 || echo 'NAS_TIMEOUT'")
        
        nas_available = "NAS_TIMEOUT" not in out and exit_code == 0
        
        if nas_available:
            print("    NAS is accessible, using volume mount")
            volume_mount = "-v /opt/mycosoft/media/website/assets:/app/public/assets:ro"
        else:
            print("    NAS not accessible, starting WITHOUT NAS mount")
            volume_mount = ""

        # Start container
        print("\n[9] Starting website container...")
        run_cmd(client, f"""docker run -d \
            --name {CONTAINER_NAME} \
            -p 3000:3000 \
            --network mycosoft-network \
            --restart unless-stopped \
            {volume_mount} \
            mycosoft-always-on-mycosoft-website:latest 2>&1""")

        print("\n[10] Waiting for startup (20s)...")
        time.sleep(20)

        # Verify
        print("\n[11] Verifying container...")
        run_cmd(client, f"docker ps --filter name={CONTAINER_NAME}")
        run_cmd(client, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/ || echo 'FAIL'")

        # Check for new content
        print("\n[12] Checking for device pages...")
        run_cmd(client, "curl -s http://localhost:3000/devices | grep -c 'SporeBase' || echo '0'")

        print("\n" + "=" * 60)
        print("  DONE - Now purge Cloudflare and hard refresh browser")
        print("=" * 60)

    except Exception as e:
        print(f"[ERROR] {e}")
        return 1
    finally:
        client.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
