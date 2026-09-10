"""Persist NLM NAS paths on MAS 188. No model blobs on root. No secrets printed."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

CREDS = Path(__file__).resolve().parents[1] / ".credentials.local"
HOST = "192.168.0.188"
ENV_PATH = "/home/mycosoft/mycosoft/mas/.env"
MARKER = "NLM_HOME=/mnt/mycosoft-nas/models/nlm"


def load_creds() -> None:
    if not CREDS.exists():
        raise SystemExit("missing .credentials.local")
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def run(ssh: paramiko.SSHClient, command: str) -> tuple[int, str, str]:
    _, stdout, stderr = ssh.exec_command(command)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return stdout.channel.recv_exit_status(), out, err


def main() -> int:
    load_creds()
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    user = "mycosoft"
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        HOST,
        username=user,
        password=password or None,
        timeout=30,
        allow_agent=True,
        look_for_keys=True,
    )
    try:
        code, df, _ = run(ssh, "df -h / | tail -1")
        print("ROOT_DF", df.strip())
        used = df.split()[4] if df.split() else "?"
        used_pct = int(used.rstrip("%")) if str(used).endswith("%") else 100
        if used_pct >= 80:
            print("FAIL_CLOSED_NO_ROOT_BLOBS")
        code, ls, err = run(ssh, "test -f /mnt/mycosoft-nas/models/nlm/reference/weights.pt && echo PRESENT || echo MISSING")
        print("NAS_REF", ls.strip() or err.strip())
        sftp = ssh.open_sftp()
        try:
            with sftp.file(ENV_PATH, "r") as handle:
                current = handle.read().decode("utf-8", errors="replace")
        except FileNotFoundError:
            current = ""
        if MARKER not in current:
            addition = (
                "\n# FormSpace NLM SEP10 — NAS only, never Ollama\n"
                "NLM_HOME=/mnt/mycosoft-nas/models/nlm\n"
                "NLM_MODEL_DIR=/mnt/mycosoft-nas/models/nlm/reference\n"
            )
            with sftp.file(ENV_PATH, "a") as handle:
                handle.write(addition)
            print("NLM_ENV_APPENDED")
        else:
            print("NLM_ENV_ALREADY_PRESENT")
        sftp.close()
        code, skip, _ = run(
            ssh,
            "systemctl show mas-orchestrator -p Environment --no-pager | tr ' ' '\\n' | grep -c SKIP || true",
        )
        print("SKIP_STARTUP_MARKERS", skip.strip())
    finally:
        ssh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
