"""SFTP 188 maps env and print name/hash only. Never print values."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
CREDS = ROOT / ".credentials.local"
REMOTE = "/home/mycosoft/mycosoft/mas/.credentials.maps.env"
REMOTE_ENV = "/home/mycosoft/mycosoft/mas/.env"


def load_creds() -> None:
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def connect() -> paramiko.SSHClient:
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key_path = Path.home() / ".ssh" / "mycosoft_vm_automation_ed25519"
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
    return client


def run_sudo(client: paramiko.SSHClient, cmd: str) -> str:
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    stdin, stdout, stderr = client.exec_command(f"sudo -S -p '' {cmd}", timeout=40, get_pty=True)
    stdin.write(password + "\n")
    stdin.flush()
    stdin.channel.shutdown_write()
    out = stdout.read().decode("utf-8", "replace")
    if password:
        out = out.replace(password, "***")
    return out


def fingerprint(path: Path, label: str) -> None:
    print("LOCAL_COPY", label, "bytes", path.stat().st_size)
    needles = ("GOOGLE", "FUSARIUM", "GEMINI", "MAPS", "MAP_TILES")
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if not value or not any(n in name.upper() for n in needles):
            continue
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
        print(f"  {name} len={len(value)} prefix={value[:4]} sha256_12={digest}")


def main() -> None:
    load_creds()
    client = connect()
    dest_maps = Path(tempfile.gettempdir()) / "itdx_188_maps.env"
    dest_env = Path(tempfile.gettempdir()) / "itdx_188_mas.env"
    try:
        print(run_sudo(client, f"install -m 644 {REMOTE} /tmp/itdx_maps.env && echo COPIED_MAPS"))
        print(run_sudo(client, f"install -m 644 {REMOTE_ENV} /tmp/itdx_mas.env && echo COPIED_ENV"))
        sftp = client.open_sftp()
        try:
            sftp.get("/tmp/itdx_maps.env", str(dest_maps))
            sftp.get("/tmp/itdx_mas.env", str(dest_env))
        finally:
            sftp.close()
        print(run_sudo(client, "rm -f /tmp/itdx_maps.env /tmp/itdx_mas.env"))
        fingerprint(dest_maps, "maps.env")
        fingerprint(dest_env, "mas.env")
    finally:
        for path in (dest_maps, dest_env):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        client.close()


if __name__ == "__main__":
    main()
