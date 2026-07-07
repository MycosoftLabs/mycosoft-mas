#!/usr/bin/env python3
"""One-shot Jetson I2C rescan + psathyrella agent restart."""
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
    host = os.environ.get("JETSON_IP", "192.168.0.123")
    user = os.environ.get("JETSON_SSH_USER", "jetson")
    password = os.environ.get("JETSON_SSH_PASSWORD") or os.environ.get("VM_PASSWORD", "")
    if not password:
        print("Missing JETSON_SSH_PASSWORD or VM_PASSWORD", file=sys.stderr)
        return 1

    remote_script = f"""#!/bin/bash
set +e
PASS={password!r}
run_sudo() {{ echo "$PASS" | sudo -S "$@" 2>&1; }}
echo "=== i2c bus list ==="
ls -1 /dev/i2c-* 2>/dev/null || true
run_sudo i2cdetect -l 2>/dev/null || i2cdetect -l 2>/dev/null || true
echo "=== scan all buses (full grid bus 1) ==="
run_sudo i2cdetect -y -r 1
for b in 0 2 4 5 7 8 9; do
  if [ -e /dev/i2c-$b ]; then
    echo "=== bus $b (non-empty rows only) ==="
    run_sudo i2cdetect -y -r $b | awk 'NR==1 || /[0-9a-fA-F][0-9a-fA-F]:/ {{print}}' | grep -v ': -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --' || true
  fi
done
echo "=== blinka scan ==="
/home/jetson/.openclaw/venvs/psathyrella-agent/bin/python <<'PY'
import board, busio
print("SCL", board.SCL, "SDA", board.SDA)
for label, scl, sda in [("default", board.SCL, board.SDA)]:
    try:
        i2c = busio.I2C(scl, sda)
        while not i2c.try_lock():
            pass
        addrs = i2c.scan()
        i2c.unlock()
        print(label, "scan", [hex(a) for a in addrs])
    except Exception as e:
        print(label, "err", e)
try:
    scl, sda = board.SCL_1, board.SDA_1
    print("SCL_1", scl, "SDA_1", sda)
    i2c = busio.I2C(scl, sda)
    while not i2c.try_lock():
        pass
    addrs = i2c.scan()
    i2c.unlock()
    print("SCL_1 scan", [hex(a) for a in addrs])
except Exception as e:
    print("SCL_1 err", e)
PY
echo "=== sysfs bus 1 ==="
for d in /sys/bus/i2c/devices/1-00*/name; do
  [ -f "$d" ] && echo "$(basename $(dirname $d)): $(cat $d)"
done
echo "=== restart agent ==="
systemctl --user restart psathyrella-agent
sleep 3
curl -s http://127.0.0.1:8788/health
echo
"""

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=user, password=password, timeout=15)
    except Exception as exc:
        print(f"SSH failed to {user}@{host}: {exc}", file=sys.stderr)
        return 2

    stdin, stdout, stderr = ssh.exec_command("bash -s", timeout=90)
    stdin.write(remote_script)
    stdin.channel.shutdown_write()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    ssh.close()

    print(out)
    if err.strip():
        print(err, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
