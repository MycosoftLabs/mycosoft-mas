"""Inspect 188 for gcloud/ADC/maps env. Never print secret values."""

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
    cmd = r"""
set -e
echo GCLOUD=$(command -v gcloud || echo missing)
if [ -f "$HOME/.config/gcloud/application_default_credentials.json" ]; then echo ADC_HOME=yes; else echo ADC_HOME=no; fi
if [ -f /home/mycosoft/mycosoft/mas/.credentials.maps.env ]; then
  echo MAPS_ENV=yes
  cut -d= -f1 /home/mycosoft/mycosoft/mas/.credentials.maps.env
else
  echo MAPS_ENV=no
fi
echo ORCH=$(systemctl is-active mas-orchestrator)
systemctl show mas-orchestrator -p EnvironmentFiles --no-pager
PID=$(systemctl show mas-orchestrator -p MainPID --value)
if [ -n "$PID" ] && [ "$PID" != "0" ]; then
  tr '\0' '\n' < /proc/$PID/environ | awk -F= '/GOOGLE|GCP_|GCLOUD|SERVICE_ACCOUNT/ {print $1}' | sort -u
fi
find /home/mycosoft /opt -maxdepth 5 \( -name 'service_account.json' -o -name 'application_default_credentials.json' \) 2>/dev/null | head
"""
    stdin, stdout, stderr = client.exec_command(cmd, timeout=40)
    print(stdout.read().decode("utf-8", "replace"))
    err = stderr.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[:500])
    client.close()


if __name__ == "__main__":
    main()
