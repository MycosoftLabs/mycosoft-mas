"""Mount Mycosoft NAS on MAS 188 for scientific NLM only. Do not print secrets."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

CREDS = Path(__file__).resolve().parents[1] / ".credentials.local"
HOST = "192.168.0.188"
NAS_SHARE = "//192.168.0.105/mycosoft.com"
MOUNT = "/mnt/mycosoft-nas"
NLM_TREE = "/mnt/mycosoft-nas/models/nlm"
MYCA_TREE = "/mnt/mycosoft-nas/models/myca"
CRED_FILE = "/etc/samba/mycosoft-nas.creds"
FSTAB_LINE = (
    f"{NAS_SHARE} {MOUNT} cifs "
    f"credentials={CRED_FILE},vers=3.0,iocharset=utf8,"
    "uid=1000,gid=1000,file_mode=0644,dir_mode=0755,nofail,_netdev 0 0"
)


def load_creds() -> None:
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def connect() -> paramiko.SSHClient:
    user = os.environ.get("VM_SSH_USER") or os.environ.get("MAS_VM_USER") or "mycosoft"
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key_paths = [
        Path.home() / ".ssh" / "mycosoft_vm_automation_ed25519",
        Path.home() / ".ssh" / "mycosoft_vm_ed25519",
        Path.home() / ".ssh" / "id_ed25519",
    ]
    last_error = "no auth method"
    for key_path in key_paths:
        if not key_path.exists():
            continue
        try:
            ssh.connect(
                HOST,
                username=user,
                key_filename=str(key_path),
                timeout=25,
                allow_agent=False,
                look_for_keys=False,
            )
            print(f"connected via key {key_path.name}")
            return ssh
        except Exception as exc:  # noqa: BLE001
            last_error = f"{key_path.name}:{type(exc).__name__}"
            print(last_error)
    if password:
        try:
            ssh.connect(
                HOST,
                username=user,
                password=password,
                timeout=25,
                allow_agent=False,
                look_for_keys=False,
            )
            print("connected via password")
            return ssh
        except Exception as exc:  # noqa: BLE001
            last_error = f"password:{type(exc).__name__}"
            print(last_error)
    raise SystemExit(f"FAILED connect 188: {last_error}")


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 90) -> tuple[int, str, str]:
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout, get_pty=True)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    rc = stdout.channel.recv_exit_status()
    return rc, out, err


def sudo(ssh: paramiko.SSHClient, cmd: str, timeout: int = 90) -> tuple[int, str, str]:
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    wrapped = f"sudo -S -p '' bash -lc {repr(cmd)}"
    stdin, stdout, stderr = ssh.exec_command(wrapped, timeout=timeout, get_pty=True)
    if password:
        stdin.write(password + "\n")
        stdin.flush()
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    rc = stdout.channel.recv_exit_status()
    return rc, out, err


def redact(text: str) -> str:
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    nas_pw = os.environ.get("NAS_SMB_PASSWORD") or ""
    for secret in (password, nas_pw):
        if secret:
            text = text.replace(secret, "<redacted>")
    return text


def main() -> int:
    load_creds()
    nas_user = os.environ.get("NAS_SMB_USER") or ""
    nas_pw = os.environ.get("NAS_SMB_PASSWORD") or ""
    if not nas_user or not nas_pw:
        print("NAS SMB credentials missing")
        return 2

    ssh = connect()
    try:
        print("==== preflight ====")
        for cmd in (
            "df -h / /home /opt /usr /var",
            "free -h | sed -n '1,3p'",
            "ls -ld /mnt /opt/mycosoft /opt/mycosoft/media /usr/share/ollama 2>/dev/null || true",
            "findmnt -t cifs || true",
            "systemctl is-active mas-orchestrator || true",
            "ls /etc/systemd/system/mas-orchestrator.service.d 2>/dev/null || true",
        ):
            rc, out, err = run(ssh, cmd)
            print(f"-- {cmd} rc={rc}")
            print(redact(out)[:2000])
            if err.strip():
                print("ERR", redact(err)[:300])

        print("==== write nas creds and persist mount ====")
        creds_body = f"username={nas_user}\npassword={nas_pw}\n"
        sftp = ssh.open_sftp()
        with sftp.file("/tmp/mycosoft-nas.creds", "w") as handle:
            handle.write(creds_body)
        sftp.chmod("/tmp/mycosoft-nas.creds", 0o600)
        sftp.close()

        setup = f"""
set -e
mkdir -p {MOUNT} /etc/samba
install -m 600 /tmp/mycosoft-nas.creds {CRED_FILE}
rm -f /tmp/mycosoft-nas.creds
if ! grep -q '{NAS_SHARE}' /etc/fstab; then
  echo '{FSTAB_LINE}' >> /etc/fstab
fi
if ! mountpoint -q {MOUNT}; then
  echo WAITING_FOR_SHARED_NAS_MOUNT
  mount {MOUNT} || mount -t cifs {NAS_SHARE} {MOUNT} -o credentials={CRED_FILE},vers=3.0,iocharset=utf8,uid=1000,gid=1000,file_mode=0644,dir_mode=0755
fi
mkdir -p {NLM_TREE}/incoming
# Sibling owns {MYCA_TREE} for Ollama GGUF. Never copy GGUF here.
chown -R mycosoft:mycosoft {NLM_TREE} || true
echo NLM_TREE_OK
mountpoint {MOUNT} || true
df -h {MOUNT} || true
ls -la {MOUNT}/models 2>/dev/null || ls -la {MOUNT} | sed -n '1,40p'
ls -la {NLM_TREE}
ls -la {MYCA_TREE} 2>/dev/null || echo MYCA_TREE_NOT_YET
"""
        rc, out, err = sudo(ssh, setup, timeout=120)
        print(f"setup rc={rc}")
        print(redact(out)[:4000])
        if err.strip():
            print("ERR", redact(err)[:800])
        if rc != 0:
            return rc

        print("==== search NAS for scientific NLM checkpoints ====")
        search = f"""
python3 - <<'PY'
from pathlib import Path
mount = Path('{MOUNT}')
nlm = Path('{NLM_TREE}')
print('TOP', [p.name for p in mount.iterdir()] if mount.exists() else 'missing')
print('NLM_TREE', list(nlm.rglob('*'))[:50] if nlm.exists() else 'missing')
skip = {{'personaplex','ollama','.git','node_modules','website','assets','mindex'}}
candidates = []
for child in (list(mount.iterdir()) if mount.exists() else []):
    low = child.name.lower()
    if any(s in low for s in ('nlm','formspace','nature')):
        candidates.append(child)
    if child.is_dir() and low in {{'models','ai','ml','training','science','mas'}}:
        candidates.append(child)
# shallow walk depth 3 on candidates + nlm tree
found = []
seen = set()
for root in [nlm, *candidates]:
    if not root.exists():
        continue
    for path in root.rglob('*'):
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        if len(rel.parts) > 4:
            continue
        text = str(path).lower()
        if any(s in text for s in skip):
            continue
        if path.is_dir() and any(k in text for k in ('nlm','formspace','nature-learning')):
            print('DIR', path)
        if path.is_file() and path.suffix.lower() in {{'.pt','.pth','.safetensors'}}:
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size >= 1_000_000:
                found.append((size, str(path)))
print('hits', len(found))
for size, path in sorted(found, reverse=True)[:40]:
    print(size, path)
PY
"""
        rc, out, err = run(ssh, search, timeout=120)
        print(f"search rc={rc}")
        print(redact(out)[:5000])
        if err.strip():
            print("ERR", redact(err)[:500])
        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    sys.exit(main())
