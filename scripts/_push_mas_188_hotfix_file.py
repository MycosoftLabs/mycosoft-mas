#!/usr/bin/env python3
"""Push local myca_main.py hotfix to MAS VM 188 and restart service."""
from __future__ import annotations

import os
import posixpath
import time
from pathlib import Path

import paramiko

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_FILE = REPO_ROOT / "mycosoft_mas" / "core" / "myca_main.py"
REMOTE_FILE = "/home/mycosoft/mycosoft/mas/mycosoft_mas/core/myca_main.py"


def load_password() -> str:
    creds_file = REPO_ROOT / ".credentials.local"
    for line in creds_file.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    if not password:
        raise RuntimeError("VM password missing in .credentials.local")
    return password


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 180) -> tuple[int, str, str]:
    _stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    rc = stdout.channel.recv_exit_status()
    return rc, out, err


def ensure_env_flag(ssh: paramiko.SSHClient, name: str, value: str) -> None:
    cmd = (
        f"if grep -q '^{name}=' /home/mycosoft/mycosoft/mas/.env; then "
        f"sed -i \"s/^{name}=.*/{name}={value}/\" /home/mycosoft/mycosoft/mas/.env; "
        f"else echo '{name}={value}' >> /home/mycosoft/mycosoft/mas/.env; fi"
    )
    rc, out, err = run(ssh, cmd)
    print(f"[env] {name}={value} rc={rc}")
    if out.strip():
        print(out[:800])
    if err.strip():
        print(err[:400])


def main() -> int:
    password = load_password()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.188", username="mycosoft", password=password, timeout=45)

    # Backup current remote file
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup = f"{REMOTE_FILE}.bak_hotfix_{ts}"
    rc, out, err = run(ssh, f"cp {REMOTE_FILE} {backup}")
    print(f"[backup] rc={rc} -> {backup}")
    if err.strip():
        print(err[:500])

    # Upload local hotfix file
    sftp = ssh.open_sftp()
    remote_tmp = posixpath.join("/tmp", f"myca_main_hotfix_{ts}.py")
    sftp.put(str(LOCAL_FILE), remote_tmp)
    sftp.close()

    rc, out, err = run(ssh, f"cp {remote_tmp} {REMOTE_FILE}")
    print(f"[upload] rc={rc}")
    if err.strip():
        print(err[:500])

    ensure_env_flag(ssh, "STATIC_BUILD_ON_STARTUP", "0")
    ensure_env_flag(ssh, "MAS_SKIP_BACKGROUND_STARTUP", "1")

    # Restart systemd service with sudo
    chan = ssh.get_transport().open_session()
    chan.get_pty()
    chan.exec_command("sudo -S systemctl restart mas-orchestrator")
    chan.send(password + "\n")
    while not chan.exit_status_ready():
        time.sleep(0.25)
    print(f"[restart] rc={chan.recv_exit_status()}")
    chan.close()

    # Probe endpoints
    probe = (
        "for u in /version /live /ready /health /api/myca/ping; do "
        "echo \"---${u}---\"; "
        "curl -sS -m 8 -w '\\nCODE:%{http_code}\\n' \"http://127.0.0.1:8001${u}\" || true; "
        "done"
    )
    rc, out, err = run(ssh, "sleep 6; " + probe, timeout=180)
    print(f"[probe] rc={rc}\n{out[:5000]}")
    if err.strip():
        print("probe stderr:", err[:2000])

    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
