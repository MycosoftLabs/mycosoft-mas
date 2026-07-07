#!/usr/bin/env python3
"""Patch live Jetson agent PCA9685 address to 0x60 and restart."""
import os
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


AGENT = "/home/jetson/.openclaw/workspace/tools/psathyrella-agent/jetson_agent.py"
OLD = "                self._pca = PCA9685(i2c)  # addr 0x40 default — `sudo i2cdetect -y -r 1` must show 0x40"
NEW = (
    "                _pca_addr = int(os.getenv(\"PCA9685_I2C_ADDRESS\", \"0x60\"), 0)\n"
    "                self._pca = PCA9685(i2c, address=_pca_addr)"
)


def main() -> int:
    load_credentials()
    password = os.environ.get("JETSON_SSH_PASSWORD") or os.environ.get("VM_PASSWORD", "")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.123", username="jetson", password=password, timeout=15)

    sftp = ssh.open_sftp()
    with sftp.open(AGENT, "r") as f:
        text = f.read().decode("utf-8")

    if OLD not in text and "PCA9685_I2C_ADDRESS" in text:
        print("Already patched")
    elif OLD in text:
        text = text.replace(OLD, NEW)
        with sftp.open(AGENT, "w") as f:
            f.write(text)
        print("Patched agent PCA address env (default 0x60)")
    else:
        print("Could not find expected PCA9685 line — manual patch needed", file=sys.stderr)
        sftp.close()
        ssh.close()
        return 1

    remote = """#!/bin/bash
set -e
mkdir -p ~/.config/systemd/user/psathyrella-agent.service.d
cat > ~/.config/systemd/user/psathyrella-agent.service.d/pca-address.conf <<'EOF'
[Service]
Environment=PCA9685_I2C_ADDRESS=0x60
EOF
systemctl --user daemon-reload
systemctl --user restart psathyrella-agent
sleep 3
echo "=== health ==="
curl -s http://127.0.0.1:8788/health
echo
echo "=== pwm snapshot ==="
curl -s http://127.0.0.1:8788/status | head -c 1200
echo
"""
    stdin, stdout, stderr = ssh.exec_command("bash -s", timeout=60)
    stdin.write(remote)
    stdin.channel.shutdown_write()
    sys.stdout.buffer.write(stdout.read())
    err = stderr.read()
    if err:
        sys.stderr.buffer.write(err)
    sftp.close()
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
