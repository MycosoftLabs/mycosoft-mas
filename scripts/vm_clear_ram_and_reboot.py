#!/usr/bin/env python3
"""Clear RAM cache on VMs and reboot MAS. Use when OOM during builds."""
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CREDS_FILE = REPO_ROOT / ".credentials.local"
if not CREDS_FILE.exists():
    print("ERROR: .credentials.local not found")
    sys.exit(1)
for line in CREDS_FILE.read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

password = os.environ.get("VM_SSH_PASSWORD") or os.environ.get("VM_PASSWORD")
if not password:
    print("ERROR: VM_SSH_PASSWORD or VM_PASSWORD not set")
    sys.exit(1)

try:
    import paramiko
except ImportError:
    print("ERROR: paramiko not installed")
    sys.exit(1)

def run(host: str, user: str, cmd: str, timeout: int = 60) -> tuple[int, str, str]:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(host, username=user, password=password, timeout=30)
    _, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    c.close()
    return code, out, err

def main():
    pw_esc = password.replace("'", "'\\''")

    # 1. Sandbox 187 - drop_caches (skip if VM is unresponsive)
    print("\n--- Sandbox 187: Clear RAM cache ---")
    try:
        code, out, err = run("192.168.0.187", "mycosoft",
            f"free -m; echo '{pw_esc}' | sudo -S sh -c 'echo 3 > /proc/sys/vm/drop_caches' 2>/dev/null; free -m",
            timeout=20)
        print(out or err or f"exit={code}")
    except Exception as e:
        print(f"  Sandbox slow/unresponsive (OOM?): {e}")

    # 2. MAS 188 - clear cache then reboot
    print("\n--- MAS 188: Clear RAM cache ---")
    try:
        code, out, err = run("192.168.0.188", "mycosoft",
            f"free -m; echo '{pw_esc}' | sudo -S sh -c 'echo 3 > /proc/sys/vm/drop_caches' 2>/dev/null; free -m",
            timeout=20)
        print(out or err or f"exit={code}")
    except Exception as e:
        print(f"  MAS cache clear failed: {e}")

    # 3. Reboot MAS 188
    print("\n--- MAS 188: Rebooting (waiting for come-back) ---")
    try:
        code, _, _ = run("192.168.0.188", "mycosoft",
            f"echo '{pw_esc}' | sudo -S reboot 2>/dev/null || true", timeout=15)
    except Exception as e:
        print(f"  Reboot command may have failed: {e}")
    print("Reboot command sent.")
    for i in range(18, 0, -1):
        print(f"  Waiting {i*5}s for MAS to come back...")
        time.sleep(5)
        try:
            c = paramiko.SSHClient()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            c.connect("192.168.0.188", username="mycosoft", password=password, timeout=5)
            c.close()
            print("  MAS VM is back.")
            break
        except Exception:
            pass
    else:
        print("  MAS may still be booting. Check manually: ssh mycosoft@192.168.0.188")

    print("\n--- Done ---")

if __name__ == "__main__":
    main()
