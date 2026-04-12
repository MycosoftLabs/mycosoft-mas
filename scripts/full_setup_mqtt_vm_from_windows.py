#!/usr/bin/env python3
"""
From Windows: SSH to Proxmox -> stop VM -> virt-customize disk (SSH pw + qga) -> start VM
-> wait -> SSH to guest -> Mosquitto + UFW.

Requires: paramiko; Proxmox root SSH password in VM_PASSWORD / PROXMOX_PASSWORD / .credentials.local
Date: Apr 08, 2026
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
from infra.csuite.provision_base import load_credentials  # noqa: E402
from infra.csuite.provision_ssh import pve_ssh_exec  # noqa: E402


def _safe_print(text: str) -> None:
    sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()


def main() -> int:
    try:
        import paramiko
    except ImportError:
        print("ERROR: poetry run pip install paramiko", file=sys.stderr)
        return 1

    vmid = int(os.environ.get("MQTT_VM_VMID", "101"))
    pve = (os.environ.get("PVE_SSH_HOST") or "192.168.0.90").strip()
    guest_ip = (os.environ.get("MQTT_VM_GUEST_IP") or "192.168.0.196").strip()
    guest_user = (os.environ.get("MQTT_VM_SSH_USER") or "mycosoft").strip()

    creds = load_credentials()
    pve_pw = (
        (os.environ.get("PROXMOX_PASSWORD") or "").strip()
        or creds.get("proxmox_password")
        or creds.get("proxmox202_password")
        or creds.get("vm_password")
        or ""
    ).strip()
    ssh_pw = (
        (os.environ.get("MQTT_VM_SSH_PASSWORD") or os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or "")
        .strip()
        or creds.get("vm_password")
        or pve_pw
    ).strip()
    mqtt_pw = (os.environ.get("MQTT_BROKER_PASSWORD") or "").strip() or ssh_pw
    hostname = (os.environ.get("MQTT_VM_HOSTNAME") or "mycobrain-mqtt").strip()

    if not pve_pw:
        print("ERROR: Proxmox root SSH password required.", file=sys.stderr)
        return 1
    if not ssh_pw:
        print("ERROR: Guest SSH password required (VM_PASSWORD).", file=sys.stderr)
        return 1

    prep_path = Path(__file__).resolve().parent / "proxmox_disk_enable_ssh_and_qga.sh"
    prep_script = prep_path.read_text(encoding="utf-8")
    prep_b64 = base64.b64encode(prep_script.encode("utf-8")).decode("ascii")

    remote = f"""set -euo pipefail
export MQTT_VM_VMID={vmid}
export DEBIAN_FRONTEND=noninteractive
qm stop {vmid} --timeout 120 || true
sleep 3
echo {prep_b64} | base64 -d | bash
qm start {vmid}
echo "Proxmox: VM {vmid} started after disk customization."
"""
    rb64 = base64.b64encode(remote.encode("utf-8")).decode("ascii")
    skip_disk = os.environ.get("SKIP_DISK_PREP", "").strip().lower() in ("1", "true", "yes")
    if not skip_disk:
        _safe_print("=== [1/3] Proxmox: virt-customize guest disk (may take several minutes) ===")
        ok, out = pve_ssh_exec(pve, "root", pve_pw, f"echo {rb64} | base64 -d | bash", timeout=1800)
        _safe_print(out)
        if not ok:
            print("ERROR: Proxmox disk step failed.", file=sys.stderr)
            return 1
    else:
        _safe_print("=== [1/3] SKIP_DISK_PREP=1 — skipping virt-customize ===")

    _safe_print("\n=== [2/3] Waiting for guest boot + SSH ===")
    time.sleep(45)

    b64_mqtt = base64.b64encode(mqtt_pw.encode("utf-8")).decode("ascii")
    root_script = f"""set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
timedatectl set-ntp true || true
systemctl enable --now systemd-timesyncd 2>/dev/null || true
hostnamectl set-hostname {hostname} || true
systemctl restart ssh || systemctl restart sshd || true

apt-get update -y
apt-get install -y mosquitto mosquitto-clients ufw

install -d -o mosquitto -g mosquitto /var/lib/mosquitto
install -d -m 0755 /etc/mosquitto/conf.d

MQPW=$(echo {b64_mqtt} | base64 -d)
mosquitto_passwd -c -b /etc/mosquitto/passwd mycobrain "$MQPW"
chmod 0640 /etc/mosquitto/passwd
chown root:mosquitto /etc/mosquitto/passwd

cat >/etc/mosquitto/conf.d/99-mycobrain.conf <<'EOF'
listener 1883 0.0.0.0
allow_anonymous false
password_file /etc/mosquitto/passwd
persistence true
persistence_location /var/lib/mosquitto/
log_dest file /var/log/mosquitto/mosquitto.log
log_type error
log_type warning
log_type notice
log_type information
autosave_interval 60
EOF

systemctl enable mosquitto
systemctl restart mosquitto

ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 1883/tcp comment 'MQTT'
ufw --force enable

systemctl restart qemu-guest-agent || true
timedatectl status || true
systemctl --no-pager status mosquitto || true
ufw status verbose || true
"""

    _safe_print(f"=== [3/3] Guest {guest_user}@{guest_ip}: Mosquitto + UFW ===")
    client = None
    for attempt in range(18):
        try:
            client = ssh_client_try_keys_password_kbd(guest_ip, guest_user, ssh_pw, timeout=25.0)
            break
        except Exception as e:
            if attempt == 17:
                print(f"ERROR: Guest SSH failed: {e}", file=sys.stderr)
                return 1
            _safe_print(f"  retry {attempt + 1}/18: {e}")
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
    _safe_print(out)
    if err.strip():
        sys.stderr.buffer.write(err.encode("utf-8", errors="replace"))
        sys.stderr.buffer.write(b"\n")
        sys.stderr.buffer.flush()
    return 0 if code == 0 else code


if __name__ == "__main__":
    raise SystemExit(main())
