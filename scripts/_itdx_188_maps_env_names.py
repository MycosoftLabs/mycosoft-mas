"""Read maps env names on 188 with sudo. Never print values."""

from __future__ import annotations

import os
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    for line in (ROOT / ".credentials.local").read_text(encoding="utf-8", errors="replace").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    key_path = Path.home() / ".ssh" / "mycosoft_vm_automation_ed25519"
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        "192.168.0.188",
        username="mycosoft",
        pkey=paramiko.Ed25519Key.from_private_key_file(str(key_path)),
        timeout=20,
        allow_agent=False,
        look_for_keys=False,
    )
    cmd = (
        "cut -d= -f1 /home/mycosoft/mycosoft/mas/.credentials.maps.env; "
        "systemctl is-active mas-orchestrator; "
        "systemctl show mas-orchestrator -p EnvironmentFiles --no-pager; "
        "PID=$(systemctl show mas-orchestrator -p MainPID --value); "
        "tr '\\0' '\\n' < /proc/$PID/environ | awk -F= '/GOOGLE|GCP_|GCLOUD|SERVICE_ACCOUNT/ {print $1}' | sort -u"
    )
    stdin, stdout, stderr = client.exec_command(f"sudo -S -p '' {cmd}", timeout=40, get_pty=True)
    stdin.write(password + "\n")
    stdin.flush()
    stdin.channel.shutdown_write()
    out = stdout.read().decode("utf-8", "replace")
    if password:
        out = out.replace(password, "***")
    print(out)
    client.close()


if __name__ == "__main__":
    main()
