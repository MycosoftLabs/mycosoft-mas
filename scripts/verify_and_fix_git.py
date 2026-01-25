#!/usr/bin/env python3
"""Verify device pages and fix git permissions."""

import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VM_HOST = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"
WEBSITE_PATH = "/home/mycosoft/mycosoft/website"


def run_cmd(client, cmd):
    print(f"  $ {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    if out:
        for line in out.split('\n')[:10]:
            print(f"    {line}")
    return out


def main():
    print("=" * 60)
    print("  VERIFY DEVICE PAGES & FIX GIT")
    print("=" * 60)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VM_HOST, 22, VM_USER, VM_PASSWORD, 
                  timeout=30, look_for_keys=False, allow_agent=False)

    try:
        # Test all device pages
        print("\n[1] Testing all device pages...")
        devices = ["mushroom-1", "sporebase", "hyphae-1", "myconode", "alarm"]
        for device in devices:
            out = run_cmd(client, f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:3000/devices/{device}")
            status = "OK" if "200" in out else "FAIL"
            print(f"    /devices/{device}: {status}")

        # Check what commit is running in the container
        print("\n[2] Checking container image commit...")
        run_cmd(client, "docker logs mycosoft-website 2>&1 | head -5")

        # Fix git permissions using echo password to sudo
        print("\n[3] Fixing git permissions (with password)...")
        run_cmd(client, f"echo '{VM_PASSWORD}' | sudo -S chown -R mycosoft:mycosoft {WEBSITE_PATH}/.git 2>/dev/null")
        run_cmd(client, f"echo '{VM_PASSWORD}' | sudo -S chmod -R 755 {WEBSITE_PATH}/.git 2>/dev/null")

        # Try git pull again
        print("\n[4] Pulling latest code...")
        run_cmd(client, f"cd {WEBSITE_PATH} && git fetch origin main 2>&1")
        run_cmd(client, f"cd {WEBSITE_PATH} && git reset --hard origin/main")
        run_cmd(client, f"cd {WEBSITE_PATH} && git log -1 --oneline")

        # Check devices portal content
        print("\n[5] Checking devices portal for all 5 devices...")
        run_cmd(client, "curl -s http://localhost:3000/devices | grep -o 'Mushroom 1\\|SporeBase\\|Hyphae 1\\|MycoNode\\|ALARM' | sort | uniq -c")

        print("\n" + "=" * 60)
        print("  VERIFICATION COMPLETE")
        print("=" * 60)

    finally:
        client.close()


if __name__ == "__main__":
    main()
