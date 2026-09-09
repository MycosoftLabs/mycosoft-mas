"""Read-only preflight of 188 disk, NAS mount, and Ollama. No secrets printed."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

CREDS = Path(__file__).resolve().parents[1] / ".credentials.local"
HOST = "192.168.0.188"


def load_creds() -> None:
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def redact(text: str) -> str:
    for key in ("VM_PASSWORD", "VM_SSH_PASSWORD", "NAS_SMB_PASSWORD"):
        secret = os.environ.get(key) or ""
        if secret:
            text = text.replace(secret, "<redacted>")
    return text


def connect() -> paramiko.SSHClient:
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    key_paths = [
        Path.home() / ".ssh" / "mycosoft_vm_automation_ed25519",
        Path.home() / ".ssh" / "mycosoft_vm_ed25519",
        Path.home() / ".ssh" / "id_ed25519",
    ]
    last_error = "no auth"
    for user in ("mycosoft", "root"):
        for key_path in key_paths:
            if not key_path.exists():
                continue
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh.connect(
                    HOST,
                    username=user,
                    key_filename=str(key_path),
                    timeout=25,
                    allow_agent=False,
                    look_for_keys=False,
                )
                print(f"connected as {user} via {key_path.name}")
                return ssh
            except Exception as exc:  # noqa: BLE001
                last_error = f"{user}/{key_path.name}:{type(exc).__name__}"
                print(last_error)
        if password:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                ssh.connect(
                    HOST,
                    username=user,
                    password=password,
                    timeout=25,
                    allow_agent=False,
                    look_for_keys=False,
                )
                print(f"connected as {user} via password")
                return ssh
            except Exception as exc:  # noqa: BLE001
                last_error = f"{user}/password:{type(exc).__name__}"
                print(last_error)
    raise SystemExit(f"FAILED connect 188: {last_error}")


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 60) -> tuple[int, str]:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    rc = stdout.channel.recv_exit_status()
    return rc, redact(out + (("\n" + err) if err.strip() else ""))


def main() -> int:
    load_creds()
    ssh = connect()
    try:
        commands = [
            "whoami; id; hostname",
            "df -hT / /home /opt /usr /var /tmp /mnt /mnt/mycosoft-nas 2>/dev/null || true",
            "findmnt -t cifs,nfs || true",
            "ls -ld /mnt /mnt/mycosoft-nas /mnt/mycosoft-nas/models /mnt/mycosoft-nas/models/nlm /mnt/mycosoft-nas/models/myca 2>/dev/null || true",
            "ls -la /mnt/mycosoft-nas/models 2>/dev/null || true",
            "systemctl is-active ollama mas-orchestrator docker 2>/dev/null || true",
            "systemctl cat ollama 2>/dev/null | sed -n '1,80p' || true",
            "ls -la /etc/systemd/system/ollama.service.d /usr/lib/systemd/system/ollama.service.d 2>/dev/null || true",
            "ls -la /usr/share/ollama /usr/share/ollama/.ollama /usr/share/ollama/.ollama/models 2>/dev/null || true",
            "du -sh /usr/share/ollama /usr/share/ollama/.ollama /usr/share/ollama/.ollama/models /home/mycosoft/.ollama /root/.ollama 2>/dev/null || true",
            "du -sh /usr/share/ollama/.ollama/models/blobs /usr/share/ollama/.ollama/models/manifests 2>/dev/null || true",
            "curl -sS --max-time 8 http://127.0.0.1:11434/api/tags || echo OLLAMA_TAGS_FAIL",
            "journalctl --disk-usage 2>/dev/null || true",
            "docker system df 2>/dev/null || echo NO_DOCKER_DF",
            "grep -n mycosoft-nas /etc/fstab /etc/systemd/system/*.mount 2>/dev/null || true",
            "test -f /etc/mycosoft/nlm_skip_startup && echo NLM_SKIP_FILE_PRESENT || echo NLM_SKIP_FILE_ABSENT",
            "systemctl show mas-orchestrator -p Environment --no-pager 2>/dev/null | tr ' ' '\\n' | grep -E 'NLM|OLLAMA|SKIP' || true",
        ]
        for cmd in commands:
            print(f"\n==== {cmd} ====")
            rc, text = run(ssh, cmd)
            print(f"rc={rc}")
            print(text[:4000])
        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    sys.exit(main())
