#!/usr/bin/env python3
"""
Deploy MQTT MycoBrain bridge on MAS VM (192.168.0.188).

- Pulls latest mycosoft-mas on the VM
- Installs paho-mqtt + httpx (user pip)
- Writes ~/.config/mqtt-mycobrain-bridge.env (600) with LAN URLs and secrets
  (MINDEX token read from MINDEX VM /home/mycosoft/mindex/.env; MQTT password = VM password)
- Installs and starts systemd: mqtt-mycobrain-bridge

Usage (from MAS repo root, .credentials.local present):
  python scripts/deploy_mqtt_bridge_mas_vm.py
"""
from __future__ import annotations

import io
import os
import re
import shlex
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

MAS_HOST = os.environ.get("MAS_VM_HOST", "192.168.0.188")
MINDEX_HOST = os.environ.get("MINDEX_VM_HOST", "192.168.0.189")
MAS_REPO = os.environ.get("MAS_REPO_PATH", "/home/mycosoft/mycosoft/mas")
MINDEX_ENV_PATH = os.environ.get("MINDEX_ENV_PATH", "/home/mycosoft/mindex/.env")


def load_vm_password() -> str:
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")
    if pw:
        return pw
    creds = REPO_ROOT / ".credentials.local"
    if creds.exists():
        for line in creds.read_text().splitlines():
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
                return v.strip()
    print("ERROR: VM_PASSWORD / .credentials.local", file=sys.stderr)
    sys.exit(1)


def load_mqtt_broker_password(fallback: str) -> str:
    """LAN broker auth — see docs/MQTT_LAN_WSS_DEPLOYMENT_AND_JETSON_HANDOFF_APR08_2026.md."""
    for key in ("MQTT_BROKER_PASSWORD", "MYCOBRAIN_MQTT_PASSWORD"):
        v = os.environ.get(key, "").strip()
        if v:
            return v
    creds = REPO_ROOT / ".credentials.local"
    if creds.exists():
        for line in creds.read_text().splitlines():
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() in ("MQTT_BROKER_PASSWORD", "MYCOBRAIN_MQTT_PASSWORD"):
                return v.strip()
    return fallback


def first_internal_token(env_text: str) -> str | None:
    for line in env_text.splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == "MINDEX_INTERNAL_TOKENS":
            # comma-separated or single
            part = v.strip().strip('"').strip("'")
            if not part:
                return None
            return part.split(",")[0].strip()
        if k.strip() == "MINDEX_INTERNAL_TOKEN":
            return v.strip().strip('"').strip("'") or None
    return None


def sftp_read_text(client, path: str) -> str | None:
    try:
        sftp = client.open_sftp()
        with sftp.file(path, "r") as f:
            data = f.read().decode("utf-8", errors="replace")
        sftp.close()
        return data
    except OSError:
        return None


def main() -> None:
    import paramiko

    password = load_vm_password()
    mqtt_password = load_mqtt_broker_password(password)
    user = os.environ.get("VM_SSH_USER", "mycosoft")

    # --- MINDEX: read internal token ---
    mindex = paramiko.SSHClient()
    mindex.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    mindex.connect(MINDEX_HOST, username=user, password=password, timeout=30)
    env_body = sftp_read_text(mindex, MINDEX_ENV_PATH)
    mindex.close()
    token = first_internal_token(env_body or "")
    if not token:
        print(
            "WARN: Could not read MINDEX_INTERNAL_TOKENS from MINDEX VM; "
            "bridge will log 'MINDEX_INTERNAL_TOKEN unset' until you fix ~/.config/mqtt-mycobrain-bridge.env",
            file=sys.stderr,
        )

    # --- Build env file (never print secrets) ---
    env_lines = [
        "# Written by deploy_mqtt_bridge_mas_vm.py — do not commit",
        "MAS_API_URL=http://127.0.0.1:8001",
        "MINDEX_API_URL=http://192.168.0.189:8000",
        "MQTT_BROKER_HOST=192.168.0.196",
        "MQTT_BROKER_PORT=1883",
        "MQTT_TOPIC_PREFIX=mycobrain",
        "MYCOBRAIN_MQTT_USERNAME=mycobrain",
        f"MYCOBRAIN_MQTT_PASSWORD={mqtt_password}",
        "LOG_LEVEL=INFO",
    ]
    if token:
        env_lines.append(f"MINDEX_INTERNAL_TOKEN={token}")

    env_content = "\n".join(env_lines) + "\n"
    remote_env_path = "/home/mycosoft/.config/mqtt-mycobrain-bridge.env"

    # --- MAS: write env, pip, systemd ---
    mas = paramiko.SSHClient()
    mas.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    mas.connect(MAS_HOST, username=user, password=password, timeout=30)

    # Prefer MAS repo venv (same as mas-orchestrator); else system python3
    stdin, stdout, stderr = mas.exec_command(
        f"cd {MAS_REPO} && "
        f"if [ -x venv/bin/python ]; then echo \"$(pwd)/venv/bin/python\"; "
        f"else command -v python3 || echo /usr/bin/python3; fi"
    )
    pybin = stdout.read().decode("utf-8", errors="replace").strip() or "/usr/bin/python3"
    stdout.channel.recv_exit_status()

    sftp = mas.open_sftp()
    try:
        sftp.mkdir("/home/mycosoft/.config")
    except OSError:
        pass
    with sftp.file(remote_env_path, "w") as rf:
        rf.write(env_content)
    sftp.chmod(remote_env_path, 0o600)

    unit_path_upload = "/home/mycosoft/.mqtt-mycobrain-bridge.service.upload"
    unit_body = f"""[Unit]
Description=MycoBrain MQTT bridge (MAS + MINDEX)
After=network-online.target mas-orchestrator.service
Wants=network-online.target

[Service]
Type=simple
User=mycosoft
WorkingDirectory={MAS_REPO}
Environment=PYTHONPATH={MAS_REPO}
EnvironmentFile={remote_env_path}
ExecStart={pybin} -m mycosoft_mas.integrations.mqtt_mycobrain_bridge
Restart=on-failure
RestartSec=15

[Install]
WantedBy=multi-user.target
"""
    with sftp.file(unit_path_upload, "w") as uf:
        uf.write(unit_body)
    sftp.chmod(unit_path_upload, 0o600)
    sftp.close()

    pwq = shlex.quote(password)
    systemd_path = "/etc/systemd/system/mqtt-mycobrain-bridge.service"
    py = f"""set -e
cd {MAS_REPO}
git fetch origin && git reset --hard origin/main
if [ -x venv/bin/pip ]; then
  venv/bin/pip install -q 'paho-mqtt>=2.1' 'httpx>=0.28'
else
  python3 -m pip install --user --break-system-packages -q 'paho-mqtt>=2.1' 'httpx>=0.28' || true
fi
printf '%s\\n' {pwq} | sudo -S mv {unit_path_upload} {systemd_path}
printf '%s\\n' {pwq} | sudo -S chmod 644 {systemd_path}
printf '%s\\n' {pwq} | sudo -S systemctl daemon-reload
printf '%s\\n' {pwq} | sudo -S systemctl enable mqtt-mycobrain-bridge
printf '%s\\n' {pwq} | sudo -S systemctl restart mqtt-mycobrain-bridge
sleep 3
printf '%s\\n' {pwq} | sudo -S systemctl --no-pager -l status mqtt-mycobrain-bridge || true
echo "--- journal (last 40 lines) ---"
printf '%s\\n' {pwq} | sudo -S journalctl -u mqtt-mycobrain-bridge -n 40 --no-pager || true
echo "--- curls ---"
curl -s -o /dev/null -w "MAS localhost health: %{{http_code}}\\n" http://127.0.0.1:8001/health || true
"""

    stdin, stdout, stderr = mas.exec_command(py, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    mas.close()

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except OSError:
            pass
    print(out)
    if err.strip():
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, AttributeError):
            pass
        print(err, file=sys.stderr)

    ok = "active (running)" in out.lower() or "MQTT subscribed" in out
    if not ok:
        print("Deploy finished; verify: ssh mycosoft@192.168.0.188 'sudo systemctl status mqtt-mycobrain-bridge'", file=sys.stderr)


if __name__ == "__main__":
    main()
