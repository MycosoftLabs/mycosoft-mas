#!/usr/bin/env python3
"""
Install always-on field MycoBrain services on MAS VM (192.168.0.188).

Best placement (May 2026):
  - **Heartbeat bridge** on MAS VM — probes Jetsons 123/228 every 30s → MAS registry.
    Required for production Earth Simulator (sandbox cannot reach LAN :8787).
  - **MQTT bridge** on same VM — subscribes to broker 196 when MQTT_PASSWORD is set.
    Optional supplement when agents publish mycosoft/devices/+/presence|telemetry.

NOT on the MQTT broker VM alone: that host cannot HTTP-probe the Jetson operator UIs.

Usage:
  python scripts/install_field_mycobrain_services.py
  python scripts/install_field_mycobrain_services.py --status
  python scripts/install_field_mycobrain_services.py --enable-mqtt

Requires VM_PASSWORD in .credentials.local. MQTT_PASSWORD or MYCOBRAIN_MQTT_PASSWORD
optional (MQTT service skipped if missing).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parent.parent
CREDS = ROOT / ".credentials.local"
VM_HOST = os.environ.get("MAS_VM_HOST", "192.168.0.188")
VM_USER = os.environ.get("VM_SSH_USER", "mycosoft")
MAS_DIR = "/home/mycosoft/mycosoft/mas"
ENV_FILE = f"{MAS_DIR}/.env.field-mycobrain"

FILES_TO_UPLOAD = [
    (ROOT / "scripts" / "field_mycobrain_heartbeat_bridge.py", f"{MAS_DIR}/scripts/field_mycobrain_heartbeat_bridge.py"),
    (
        ROOT / "mycosoft_mas" / "integrations" / "mqtt_mycobrain_bridge.py",
        f"{MAS_DIR}/mycosoft_mas/integrations/mqtt_mycobrain_bridge.py",
    ),
    (
        ROOT / "scripts" / "systemd" / "mycosoft-field-mycobrain-heartbeat.service",
        "/tmp/mycosoft-field-mycobrain-heartbeat.service",
    ),
    (
        ROOT / "scripts" / "systemd" / "mycosoft-mqtt-mycobrain-bridge.service",
        "/tmp/mycosoft-mqtt-mycobrain-bridge.service",
    ),
]


def load_creds() -> None:
    if CREDS.exists():
        for line in CREDS.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def connect() -> paramiko.SSHClient:
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    if not pw:
        raise SystemExit("VM_PASSWORD missing in .credentials.local")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_HOST, username=VM_USER, password=pw, timeout=20)
    return ssh


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 120) -> tuple[int, str, str]:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    code = stdout.channel.recv_exit_status()
    return code, out, err


def sudo_run(ssh: paramiko.SSHClient, cmd: str, pw: str, timeout: int = 120) -> tuple[int, str, str]:
    escaped = cmd.replace("'", "'\"'\"'")
    return run(ssh, f"echo '{pw}' | sudo -S bash -c '{escaped}'", timeout=timeout)


def upload_files(ssh: paramiko.SSHClient) -> None:
    sftp = ssh.open_sftp()
    try:
        for local, remote in FILES_TO_UPLOAD:
            if not local.exists():
                raise FileNotFoundError(local)
            remote_dir = str(Path(remote).parent).replace("\\", "/")
            try:
                sftp.stat(remote_dir)
            except OSError:
                run(ssh, f"mkdir -p '{remote_dir}'")
            sftp.put(str(local), remote)
            print(f"  uploaded {local.name} -> {remote}")
    finally:
        sftp.close()


def write_env_file(ssh: paramiko.SSHClient, enable_mqtt: bool) -> bool:
    mqtt_pass = os.environ.get("MQTT_PASSWORD") or os.environ.get("MYCOBRAIN_MQTT_PASSWORD")
    lines = [
        "# Field MycoBrain services — managed by install_field_mycobrain_services.py",
        "MAS_API_URL=http://127.0.0.1:8001",
        "MYCOBRAIN_OPERATOR_URLS=http://192.168.0.123:8787,http://192.168.0.228:8787",
        "FIELD_HEARTBEAT_INTERVAL=30",
        "MQTT_BROKER_HOST=192.168.0.196",
        "MQTT_BROKER_PORT=1883",
        "MQTT_USERNAME=mycobrain",
    ]
    has_mqtt = bool(mqtt_pass)
    if has_mqtt:
        lines.append(f"MQTT_PASSWORD={mqtt_pass}")
    content = "\n".join(lines) + "\n"
    sftp = ssh.open_sftp()
    try:
        with sftp.file(ENV_FILE, "w") as f:
            f.write(content)
    finally:
        sftp.close()
    run(ssh, f"chmod 600 '{ENV_FILE}'")
    print(f"  wrote {ENV_FILE} (mqtt_password={'yes' if has_mqtt else 'no'})")
    return has_mqtt and enable_mqtt


def install_systemd(ssh: paramiko.SSHClient, pw: str, start_mqtt: bool) -> None:
    for unit in (
        "mycosoft-field-mycobrain-heartbeat.service",
        "mycosoft-mqtt-mycobrain-bridge.service",
    ):
        sudo_run(
            ssh,
            f"cp /tmp/{unit} /etc/systemd/system/{unit} && chmod 644 /etc/systemd/system/{unit}",
            pw,
        )
    sudo_run(ssh, "systemctl daemon-reload", pw)
    sudo_run(ssh, "systemctl enable mycosoft-field-mycobrain-heartbeat.service", pw)
    sudo_run(ssh, "systemctl restart mycosoft-field-mycobrain-heartbeat.service", pw)

    if start_mqtt:
        sudo_run(ssh, "systemctl enable mycosoft-mqtt-mycobrain-bridge.service", pw)
        sudo_run(ssh, "systemctl restart mycosoft-mqtt-mycobrain-bridge.service", pw)
    else:
        sudo_run(ssh, "systemctl disable --now mycosoft-mqtt-mycobrain-bridge.service 2>/dev/null || true", pw)
        print("  MQTT bridge not started (no MQTT_PASSWORD in credentials)")


def show_status(ssh: paramiko.SSHClient, pw: str) -> None:
    for svc in ("mycosoft-field-mycobrain-heartbeat", "mycosoft-mqtt-mycobrain-bridge"):
        code, out, _ = sudo_run(ssh, f"systemctl is-active {svc}.service 2>/dev/null || echo inactive", pw)
        print(f"{svc}: {out.strip()}")
    _, out, _ = run(ssh, "curl -s http://127.0.0.1:8001/api/devices | python3 -c \"import sys,json; d=json.load(sys.stdin); ids=[x['device_id'] for x in d.get('devices',[]) if 'jetson' in x['device_id']]; print('field devices:', ids)\"")
    print(out.strip())


def main() -> int:
    load_creds()
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--enable-mqtt", action="store_true", help="Start MQTT bridge if password in creds")
    args = parser.parse_args()

    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    ssh = connect()
    try:
        if args.status:
            show_status(ssh, pw)
            return 0

        print(f"=== Installing field MycoBrain services on {VM_HOST} ===")
        upload_files(ssh)
        start_mqtt = write_env_file(ssh, enable_mqtt=args.enable_mqtt or bool(os.environ.get("MQTT_PASSWORD")))
        install_systemd(ssh, pw, start_mqtt)
        print("\n=== Status ===")
        show_status(ssh, pw)
        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    sys.exit(main())
