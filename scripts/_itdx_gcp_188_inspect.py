"""Inspect 188 for gcloud/ADC/SA/project. Never print secret values."""

from __future__ import annotations

import os
import re
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
CREDS = ROOT / ".credentials.local"
AIZA_RE = re.compile(r"AIza[0-9A-Za-z_-]{10,}")


def load_creds() -> None:
    if not CREDS.is_file():
        return
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def redact(text: str) -> str:
    text = AIZA_RE.sub("AIza***", text)
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    if password:
        text = text.replace(password, "***")
    return text


def main() -> int:
    load_creds()
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key_candidates = [
        Path.home() / ".ssh" / "mycosoft_vm_automation_ed25519",
        Path.home() / ".ssh" / "mycosoft_vm_ed25519",
        Path.home() / ".ssh" / "id_ed25519",
    ]
    connected = False
    for key_path in key_candidates:
        if not key_path.is_file():
            continue
        try:
            pkey = paramiko.Ed25519Key.from_private_key_file(str(key_path))
            client.connect(
                "192.168.0.188",
                username="mycosoft",
                pkey=pkey,
                password=password,
                timeout=25,
                allow_agent=False,
                look_for_keys=False,
            )
            print("SSH_OK key", key_path.name)
            connected = True
            break
        except Exception as exc:  # noqa: BLE001
            print("SSH_TRY_FAIL", key_path.name, type(exc).__name__)
            try:
                client.close()
            except Exception:
                pass
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if not connected:
        client.connect(
            "192.168.0.188",
            username="mycosoft",
            password=password,
            timeout=25,
            allow_agent=False,
            look_for_keys=False,
        )
        print("SSH_OK password")
    cmd = """
set +e
echo GCLOUD=$(command -v gcloud || echo missing)
echo ADC_HOME=$([ -f "$HOME/.config/gcloud/application_default_credentials.json" ] && echo yes || echo no)
echo ADC_ROOT=$([ -f /root/.config/gcloud/application_default_credentials.json ] && echo yes || echo no)
echo MAPS_ENV=$([ -f /home/mycosoft/mycosoft/mas/.credentials.maps.env ] && echo yes || echo no)
echo MAPS_NAMES=$( [ -f /home/mycosoft/mycosoft/mas/.credentials.maps.env ] && cut -d= -f1 /home/mycosoft/mycosoft/mas/.credentials.maps.env | tr '\\n' ',' )
echo UNIT=$(systemctl is-active mas-orchestrator)
echo ENVFILES=$(systemctl show mas-orchestrator -p EnvironmentFiles --no-pager)
echo SA_PATHS
for p in \
  /home/mycosoft/mycosoft/mas/credentials/google/service_account.json \
  /opt/mycosoft/credentials/google/service_account.json \
  /opt/myca/credentials/google/service_account.json \
  /home/mycosoft/.config/gcloud/application_default_credentials.json \
  /etc/google/auth/application_default_credentials.json
 do
  if [ -f "$p" ]; then echo PRESENT "$p"; else echo ABSENT "$p"; fi
done
echo FIND_SA
find /home/mycosoft /opt/mycosoft /etc/mycosoft -iname '*service*account*.json' -o -iname '*gcp*.json' -o -iname '*gcloud*' 2>/dev/null | head -40
echo CREDS_NAMES
for f in /home/mycosoft/mycosoft/mas/.credentials.local /home/mycosoft/mycosoft/mas/.env /opt/mycosoft/.credentials.local; do
  if [ -f "$f" ]; then
    echo FILE "$f"
    awk -F= '/GOOGLE_CLOUD_PROJECT|GCP_PROJECT|GCLOUD_PROJECT|GOOGLE_APPLICATION_CREDENTIALS|GCP_PROJECT_ID/ {print $1}' "$f"
  fi
done
echo PROJECT_ENV
env | awk -F= '/GOOGLE_CLOUD_PROJECT|GCP_PROJECT|GCLOUD_PROJECT|GOOGLE_APPLICATION_CREDENTIALS/ {print $1}'
"""
    stdin, stdout, stderr = client.exec_command(cmd, timeout=45)
    out = redact(stdout.read().decode("utf-8", "replace"))
    err = redact(stderr.read().decode("utf-8", "replace"))
    print(out)
    if err.strip():
        print("STDERR", err[:500])
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
