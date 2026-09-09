"""Fix ollama drop-in ExecStart conflict and prove NAS models. No secrets printed."""

from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path

import paramiko

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CREDS = Path(__file__).resolve().parents[1] / ".credentials.local"
GUARDS = Path(__file__).resolve().parent / "vm188_model_guards"
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
    return ssh


def sudo(ssh: paramiko.SSHClient, cmd: str, timeout: int = 120) -> tuple[int, str]:
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    wrapped = f"sudo -S -p '' bash -lc {shlex.quote(cmd)}"
    stdin, stdout, stderr = ssh.exec_command(wrapped, timeout=timeout, get_pty=True)
    if password:
        stdin.write(password + "\n")
        stdin.flush()
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    rc = stdout.channel.recv_exit_status()
    return rc, redact(out + (("\n" + err) if err.strip() else ""))


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 90) -> tuple[int, str]:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    rc = stdout.channel.recv_exit_status()
    return rc, redact(out + (("\n" + err) if err.strip() else ""))


def main() -> int:
    load_creds()
    ssh = connect()
    try:
        sftp = ssh.open_sftp()
        sftp.put(str(GUARDS / "ollama-nas-models.conf"), "/tmp/ollama-nas-models.conf")
        sftp.close()
        rc, text = sudo(
            ssh,
            """
set -e
# Custom .mount fights fstab generator. Keep fstab; remove bad unit.
rm -f /etc/systemd/system/mnt-mycosoft-nas.mount
systemctl daemon-reload
install -m 644 /tmp/ollama-nas-models.conf /etc/systemd/system/ollama.service.d/nas-models.conf
rm -f /tmp/ollama-nas-models.conf
# Windows editors may leave CRLF; 203/EXEC if shebang has \\r
sed -i 's/\\r$//' /usr/local/sbin/mycosoft-require-nas-models.sh /usr/local/sbin/mycosoft-disk-guard.sh /usr/local/sbin/mycosoft-ollama-wrapper.sh /usr/local/sbin/mycosoft-hf-wrapper.sh /usr/local/bin/ollama /usr/local/bin/huggingface-cli 2>/dev/null || true
chmod 755 /usr/local/sbin/mycosoft-require-nas-models.sh /usr/local/sbin/mycosoft-disk-guard.sh /usr/local/sbin/mycosoft-ollama-wrapper.sh /usr/local/bin/ollama
head -1 /usr/local/sbin/mycosoft-require-nas-models.sh | od -An -tx1 | head -1
/usr/local/sbin/mycosoft-require-nas-models.sh; echo REQUIRE_RC=$?
if [[ ! -x /usr/libexec/ollama-bin ]]; then
  echo MISSING_OLLAMA_BIN
  exit 6
fi
# Wrapper must stay a script; real ELF is libexec
if file /usr/local/bin/ollama | grep -q ELF; then
  echo WRAPPER_OVERWRITTEN
  install -m 755 /usr/local/sbin/mycosoft-ollama-wrapper.sh /usr/local/bin/ollama
fi
ls -l /usr/libexec/ollama-bin /usr/local/bin/ollama /etc/systemd/system/ollama.service.d/
findmnt -t cifs /mnt/mycosoft-nas
systemctl daemon-reload
systemctl reset-failed ollama mnt-mycosoft-nas.mount || true
systemctl start ollama
sleep 4
systemctl is-active ollama
systemctl show ollama -p DropInPaths -p ExecStart -p ExecStartPre --no-pager
""",
            timeout=60,
        )
        print(text[:4000])
        if rc != 0:
            rc2, text2 = sudo(ssh, "systemctl status ollama --no-pager -l | sed -n '1,60p'; journalctl -u ollama -n 40 --no-pager")
            print(text2[:4000])
            return rc
        prove = r"""
set -e
curl -sS --max-time 15 http://127.0.0.1:11434/api/tags
echo
for model in llama3.2:3b nemotron-3-nano:4b; do
  echo PROVE $model
  curl -sS --max-time 120 http://127.0.0.1:11434/api/generate \
    -d "{\"model\":\"$model\",\"prompt\":\"ok\",\"stream\":false,\"options\":{\"num_predict\":8}}" \
    | python3 -c 'import sys,json; d=json.load(sys.stdin); print("response_ok", bool(d.get("response"))); print("eval", d.get("eval_count"))'
done
/usr/local/sbin/mycosoft-require-nas-models.sh && echo REQUIRE_NAS_OK
/usr/local/sbin/mycosoft-disk-guard.sh; echo DISK_GUARD_RC=$?
findmnt -t cifs /mnt/mycosoft-nas
df -hT / /mnt/mycosoft-nas
lsattr -d /usr/share/ollama/.ollama/models || true
echo SKIP=$(systemctl show mas-orchestrator -p Environment --no-pager | tr ' ' '\n' | grep MAS_SKIP || true)
"""
        rc, text = run(ssh, prove, timeout=180)
        print(text[:5000])
        return rc
    finally:
        ssh.close()


if __name__ == "__main__":
    sys.exit(main())
