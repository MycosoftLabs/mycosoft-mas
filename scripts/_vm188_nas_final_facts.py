"""Collect 188 NAS/Ollama facts for the protection doc. No secrets."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CREDS = Path(__file__).resolve().parents[1] / ".credentials.local"
HOST = "192.168.0.188"


def load_creds() -> None:
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    load_creds()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        HOST,
        username="mycosoft",
        key_filename=str(Path.home() / ".ssh" / "mycosoft_vm_automation_ed25519"),
        timeout=25,
        allow_agent=False,
        look_for_keys=False,
    )
    cmd = r"""
df -hT / /mnt/mycosoft-nas
echo '---'
findmnt -n -t cifs /mnt/mycosoft-nas
echo '---'
grep mycosoft.com /etc/fstab | sed 's/password=[^,]*/password=<redacted>/g'
echo '---'
ls -la /mnt/mycosoft-nas/models /mnt/mycosoft-nas/models/nlm /mnt/mycosoft-nas/models/myca /mnt/mycosoft-nas/models/myca/ollama
echo '---'
du -sh /mnt/mycosoft-nas/models/myca/ollama /mnt/mycosoft-nas/models/nlm
echo '---'
lsattr -d /usr/share/ollama/.ollama/models 2>/dev/null || true
echo '---'
systemctl is-active ollama mas-orchestrator
echo '---'
systemctl show mas-orchestrator -p Environment --no-pager | tr ' ' '\n' | grep -E 'NLM|OLLAMA|SKIP' || true
echo '---'
test -f /etc/systemd/system/mnt-mycosoft-nas.mount && echo CUSTOM_MOUNT_UNIT_PRESENT || echo CUSTOM_MOUNT_UNIT_ABSENT
"""
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=40)
    print(stdout.read().decode("utf-8", "replace"))
    ssh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
