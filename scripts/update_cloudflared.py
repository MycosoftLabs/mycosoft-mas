#!/usr/bin/env python3
"""Update cloudflared to latest version on VM 103."""

import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VM_HOST = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"


def run_cmd(client, cmd, timeout=120):
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
    print("  UPDATE CLOUDFLARED TO LATEST VERSION")
    print("=" * 60)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VM_HOST, 22, VM_USER, VM_PASSWORD, 
                  timeout=30, look_for_keys=False, allow_agent=False)

    try:
        # Check current version
        print("\n[1] Current cloudflared version:")
        run_cmd(client, "cloudflared --version || echo 'Not installed'")

        # Check how it was installed
        print("\n[2] Checking installation method:")
        run_cmd(client, "ls -la /usr/local/etc/cloudflared/ 2>/dev/null || echo 'No package manager marker found'")
        run_cmd(client, "which cloudflared")

        # Update using apt if available
        print("\n[3] Updating via apt (if installed that way):")
        run_cmd(client, f"echo '{VM_PASSWORD}' | sudo -S apt-get update 2>&1 | tail -3")
        result = run_cmd(client, f"echo '{VM_PASSWORD}' | sudo -S apt-get install --only-upgrade cloudflared -y 2>&1")
        
        if "cloudflared is already the newest version" in result or "0 upgraded" in result:
            print("\n    Already at latest version via apt")
            # Try direct update command
            print("\n[4] Trying cloudflared self-update:")
            run_cmd(client, f"echo '{VM_PASSWORD}' | sudo -S cloudflared update 2>&1")

        # Restart the service
        print("\n[5] Restarting cloudflared service:")
        run_cmd(client, f"echo '{VM_PASSWORD}' | sudo -S systemctl restart cloudflared.service 2>&1")

        # Verify new version
        print("\n[6] Updated cloudflared version:")
        run_cmd(client, "cloudflared --version")

        # Check service status
        print("\n[7] Service status:")
        run_cmd(client, "systemctl status cloudflared.service --no-pager | head -10")

        print("\n" + "=" * 60)
        print("  CLOUDFLARED UPDATE COMPLETE")
        print("=" * 60)

    finally:
        client.close()


if __name__ == "__main__":
    main()
