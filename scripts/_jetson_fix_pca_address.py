#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path

import paramiko


def load_credentials() -> None:
    creds_file = Path(__file__).resolve().parent.parent / ".credentials.local"
    if creds_file.exists():
        for line in creds_file.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


AGENT_PATH = "/home/jetson/.openclaw/workspace/tools/psathyrella-agent/jetson_agent.py"
SERVICE_DIR = "/home/jetson/.config/systemd/user"


def main() -> int:
    load_credentials()
    password = os.environ.get("JETSON_SSH_PASSWORD") or os.environ.get("VM_PASSWORD", "")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.123", username="jetson", password=password, timeout=15)

    sftp = ssh.open_sftp()
    with sftp.open(AGENT_PATH, "r") as f:
        content = f.read().decode("utf-8")

    print("=== PCA9685 lines in agent ===")
    for i, line in enumerate(content.splitlines(), 1):
        if "PCA9685" in line or "pca9685" in line.lower() or "0x40" in line:
            print(f"{i}: {line}")

    # Patch: read address from env, default 0x60 (discovered on bus)
    if "PCA9685_I2C_ADDRESS" not in content:
        content = content.replace(
            "PCA9685(i2c)",
            'PCA9685(i2c, address=int(os.environ.get("PCA9685_I2C_ADDRESS", "0x60"), 0))',
            1,
        )
        if "PCA9685(i2c, address=int(os.environ.get" not in content:
            content = re.sub(
                r"PCA9685\(i2c(?:,\s*address\s*=\s*[^)]+)?\)",
                'PCA9685(i2c, address=int(os.environ.get("PCA9685_I2C_ADDRESS", "0x60"), 0))',
                content,
                count=1,
            )

    with sftp.open(AGENT_PATH, "w") as f:
        f.write(content)

    override = f"""[Service]
Environment=PCA9685_I2C_ADDRESS=0x60
"""
    remote = f"""#!/bin/bash
mkdir -p {SERVICE_DIR}
cat > {SERVICE_DIR}/psathyrella-agent.service.d/address.conf <<'EOF'
{override}EOF
systemctl --user daemon-reload
systemctl --user restart psathyrella-agent
sleep 3
curl -s http://127.0.0.1:8788/health
echo
journalctl --user -u psathyrella-agent -n 8 --no-pager 2>/dev/null || true
"""
    stdin, stdout, stderr = ssh.exec_command("bash -s", timeout=60)
    stdin.write(remote)
    stdin.channel.shutdown_write()
    print(stdout.read().decode())
    print(stderr.read().decode(), file=sys.stderr)
    sftp.close()
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
