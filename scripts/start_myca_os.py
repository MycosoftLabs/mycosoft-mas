#!/usr/bin/env python3
"""
Start MYCA OS — Deploy and run on VM 191.

This script:
1. SSHs to VM 191
2. Pulls latest code
3. Installs dependencies
4. Starts the MYCA OS daemon

Usage:
    # From Sandbox (187) — deploy to VM 191
    python scripts/start_myca_os.py

    # Directly on VM 191
    python scripts/start_myca_os.py --local

    # Status check
    python scripts/start_myca_os.py --status
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


VM_191 = "192.168.0.191"
VM_USER = "mycosoft"
REPO_PATH = "/home/mycosoft/repos/mycosoft-mas"
VENV_PATH = "/home/mycosoft/repos/mycosoft-mas/.venv"
LOG_PATH = "/opt/myca/logs/myca_os.log"

SSH_CMD = f"ssh {VM_USER}@{VM_191}"


def ssh_exec(command: str, check: bool = True) -> str:
    """Execute a command on VM 191 via SSH."""
    full_cmd = f'{SSH_CMD} "{command}"'
    print(f"  [VM 191] {command}")
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"  ERROR: {result.stderr[:500]}")
    return result.stdout.strip()


def deploy_remote():
    """Deploy and start MYCA OS on VM 191 via SSH."""
    print("=" * 50)
    print("Deploying MYCA OS to VM 191")
    print("=" * 50)

    # 1. Pull latest code
    print("\n[1/4] Pulling latest code...")
    ssh_exec(f"cd {REPO_PATH} && git pull origin main")

    # 2. Install/update dependencies
    print("\n[2/4] Installing dependencies...")
    ssh_exec(f"cd {REPO_PATH} && {VENV_PATH}/bin/pip install -e . 2>/dev/null || pip install -e .")

    # 3. Ensure log directory exists
    print("\n[3/4] Setting up directories...")
    ssh_exec("sudo mkdir -p /opt/myca/logs && sudo chown -R mycosoft:mycosoft /opt/myca")

    # 4. Start MYCA OS (in tmux for persistence)
    print("\n[4/4] Starting MYCA OS daemon...")
    ssh_exec("tmux kill-session -t myca-os 2>/dev/null || true")
    ssh_exec(
        f"tmux new-session -d -s myca-os "
        f"'cd {REPO_PATH} && "
        f"python -m mycosoft_mas.myca.os 2>&1 | tee -a {LOG_PATH}'"
    )

    print("\n" + "=" * 50)
    print("MYCA OS started in tmux session 'myca-os'")
    print(f"Logs: {LOG_PATH}")
    print(f"Attach: ssh {VM_USER}@{VM_191} -t 'tmux attach -t myca-os'")
    print("=" * 50)


def start_local():
    """Start MYCA OS locally (when running directly on VM 191)."""
    print("Starting MYCA OS locally...")
    os.makedirs("/opt/myca/logs", exist_ok=True)
    subprocess.run(
        [sys.executable, "-m", "mycosoft_mas.myca.os"],
        cwd=str(Path(__file__).parent.parent),
    )


def check_status():
    """Check if MYCA OS is running on VM 191."""
    print("Checking MYCA OS status on VM 191...")
    result = ssh_exec("tmux has-session -t myca-os 2>/dev/null && echo 'RUNNING' || echo 'STOPPED'", check=False)
    print(f"  Status: {result}")

    if "RUNNING" in result:
        print("\nRecent logs:")
        logs = ssh_exec(f"tail -20 {LOG_PATH}", check=False)
        print(logs)


def main():
    parser = argparse.ArgumentParser(description="Start MYCA OS on VM 191")
    parser.add_argument("--local", action="store_true", help="Start locally (on VM 191)")
    parser.add_argument("--status", action="store_true", help="Check if MYCA OS is running")
    parser.add_argument("--stop", action="store_true", help="Stop MYCA OS")
    args = parser.parse_args()

    if args.status:
        check_status()
    elif args.stop:
        print("Stopping MYCA OS...")
        ssh_exec("tmux send-keys -t myca-os C-c 2>/dev/null; sleep 2; tmux kill-session -t myca-os 2>/dev/null || true")
        print("Stopped.")
    elif args.local:
        start_local()
    else:
        deploy_remote()


if __name__ == "__main__":
    main()
