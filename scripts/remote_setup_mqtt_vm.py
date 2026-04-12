#!/usr/bin/env python3
"""
SSH to MQTT broker guest and configure Mosquitto + UFW (non-interactive).

Env:
  MQTT_VM_GUEST_IP   default 192.168.0.196
  MQTT_VM_SSH_USER   default mycosoft
  VM_PASSWORD / VM_SSH_PASSWORD
  MQTT_BROKER_PASSWORD — user mycobrain (default: same as SSH password)
  MQTT_VM_HOSTNAME   default mycobrain-mqtt
"""
from __future__ import annotations

import base64
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from infra.csuite.paramiko_ssh_dual import ssh_client_try_keys_password_kbd  # noqa: E402


def main() -> int:
    try:
        import paramiko  # noqa: F401
    except ImportError:
        print("ERROR: pip install paramiko", file=sys.stderr)
        return 1

    host = (os.environ.get("MQTT_VM_GUEST_IP") or "192.168.0.196").strip()
    user = (os.environ.get("MQTT_VM_SSH_USER") or "mycosoft").strip()
    ssh_pw = (
        (os.environ.get("MQTT_VM_SSH_PASSWORD") or os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or "")
        .strip()
    )
    mqtt_pw = (os.environ.get("MQTT_BROKER_PASSWORD") or ssh_pw).strip()
    hostname = (os.environ.get("MQTT_VM_HOSTNAME") or "mycobrain-mqtt").strip()

    if not ssh_pw:
        print("ERROR: Set MQTT_VM_SSH_PASSWORD, VM_PASSWORD, or VM_SSH_PASSWORD", file=sys.stderr)
        return 1
    if not mqtt_pw:
        print("ERROR: Set MQTT_BROKER_PASSWORD or VM_PASSWORD", file=sys.stderr)
        return 1

    b64_mqtt = base64.b64encode(mqtt_pw.encode("utf-8")).decode("ascii")

    root_script = f"""set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
timedatectl set-ntp true || true
systemctl enable --now systemd-timesyncd 2>/dev/null || true
hostnamectl set-hostname {hostname} || true

apt-get update -y
apt-get install -y mosquitto mosquitto-clients ufw

install -d -o mosquitto -g mosquitto /var/lib/mosquitto
install -d -m 0755 /etc/mosquitto/conf.d

MQPW=$(echo {b64_mqtt} | base64 -d)
mosquitto_passwd -c -b /etc/mosquitto/passwd mycobrain "$MQPW"
chmod 0640 /etc/mosquitto/passwd
chown root:mosquitto /etc/mosquitto/passwd

cat >/etc/mosquitto/conf.d/99-mycobrain.conf <<'EOF'
persistence true
persistence_location /var/lib/mosquitto/
log_dest file /var/log/mosquitto/mosquitto.log
log_type error
log_type warning
log_type notice
log_type information
autosave_interval 60
per_listener_settings true
listener 1883 0.0.0.0
protocol mqtt
allow_anonymous false
password_file /etc/mosquitto/passwd
listener 9001 0.0.0.0
protocol websockets
allow_anonymous false
password_file /etc/mosquitto/passwd
allow_origin *
EOF

systemctl enable mosquitto
systemctl restart mosquitto

ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 1883/tcp comment 'MQTT LAN'
ufw allow from 192.168.0.187 to any port 9001 proto tcp comment 'MQTT WS tunnel host'
ufw --force enable

echo '--- timedatectl ---'
timedatectl status || true
echo '--- mosquitto ---'
systemctl --no-pager status mosquitto || true
echo '--- ufw ---'
ufw status verbose || true
"""

    client = None
    for attempt in range(12):
        try:
            client = ssh_client_try_keys_password_kbd(host, user, ssh_pw, timeout=25.0)
            break
        except Exception as e:
            if attempt == 11:
                print(f"ERROR: SSH failed after retries: {e}", file=sys.stderr)
                return 1
            sys.stdout.buffer.write(
                f"SSH not ready ({e}); retry {attempt + 1}/12 ...\n".encode("utf-8", errors="replace")
            )
            sys.stdout.buffer.flush()
            time.sleep(10)
    if client is None:
        return 1

    stdin, stdout, stderr = client.exec_command("sudo -S bash -s", get_pty=True)
    stdin.write(ssh_pw + "\n")
    stdin.write(root_script)
    stdin.channel.shutdown_write()

    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    client.close()

    sys.stdout.buffer.write((out + "\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()
    if err.strip():
        sys.stderr.buffer.write(err.encode("utf-8", errors="replace"))
        sys.stderr.buffer.write(b"\n")
        sys.stderr.buffer.flush()
    return 0 if code == 0 else code


if __name__ == "__main__":
    raise SystemExit(main())
