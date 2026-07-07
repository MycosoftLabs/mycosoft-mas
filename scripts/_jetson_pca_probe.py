#!/usr/bin/env python3
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


def main() -> int:
    load_credentials()
    password = os.environ.get("JETSON_SSH_PASSWORD") or os.environ.get("VM_PASSWORD", "")
    remote_script = f"""#!/bin/bash
set +e
PASS={password!r}
run_sudo() {{ echo "$PASS" | sudo -S "$@" 2>&1; }}
echo "=== bus 7 full grid ==="
run_sudo i2cdetect -y -r 7
for addr in 40 41 42 43 60 70; do
  echo "=== i2cget bus7 0x$addr reg0 ==="
  run_sudo i2cget -y 7 0x$addr 0x00
done
/home/jetson/.openclaw/venvs/psathyrella-agent/bin/python <<'PY'
import board, busio
from adafruit_pca9685 import PCA9685
i2c = busio.I2C(board.SCL, board.SDA)
while not i2c.try_lock():
    pass
scan = [hex(a) for a in i2c.scan()]
i2c.unlock()
print("blinka scan", scan)
for addr in [0x40, 0x41, 0x42, 0x43, 0x60, 0x70]:
    try:
        pca = PCA9685(i2c, address=addr)
        pca.frequency = 50
        print("PCA9685 init OK at", hex(addr))
    except Exception as e:
        print(hex(addr), "init fail:", e)
PY
"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.123", username="jetson", password=password, timeout=15)
    stdin, stdout, stderr = ssh.exec_command("bash -s", timeout=90)
    stdin.write(remote_script)
    stdin.channel.shutdown_write()
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err.strip():
        print(err, file=sys.stderr)
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
