#!/usr/bin/env python3
"""Update cloudflared to latest version from GitHub releases."""

import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VM_HOST = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"


def run_cmd(client, cmd, timeout=180):
    print(f"  $ {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if out:
        for line in out.split('\n')[:15]:
            print(f"    {line}")
    if err:
        for line in err.split('\n')[:5]:
            print(f"    [!] {line}")
    return out


def main():
    print("=" * 60)
    print("  UPDATE CLOUDFLARED TO 2026.1.1 FROM GITHUB")
    print("=" * 60)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VM_HOST, 22, VM_USER, VM_PASSWORD, 
                  timeout=30, look_for_keys=False, allow_agent=False)

    try:
        # Check current version
        print("\n[1] Current version:")
        run_cmd(client, "cloudflared --version")

        # Download latest .deb from GitHub
        print("\n[2] Downloading latest cloudflared from GitHub...")
        run_cmd(client, "curl --location --output /tmp/cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb")

        # Install the new version
        print("\n[3] Installing new version...")
        run_cmd(client, f"echo '{VM_PASSWORD}' | sudo -S dpkg -i /tmp/cloudflared.deb 2>&1")

        # Restart the service
        print("\n[4] Restarting cloudflared service...")
        run_cmd(client, f"echo '{VM_PASSWORD}' | sudo -S systemctl restart cloudflared.service 2>&1")

        # Verify new version
        print("\n[5] New version installed:")
        run_cmd(client, "cloudflared --version")

        # Check service status
        print("\n[6] Service status:")
        run_cmd(client, "systemctl status cloudflared.service --no-pager | head -8")

        # Clean up
        print("\n[7] Cleaning up...")
        run_cmd(client, "rm /tmp/cloudflared.deb")

        print("\n" + "=" * 60)
        print("  CLOUDFLARED UPDATED TO LATEST VERSION")
        print("=" * 60)

    finally:
        client.close()


if __name__ == "__main__":
    main()
