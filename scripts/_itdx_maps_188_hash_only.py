"""Hash 188 maps.env names only. Never print values."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
CREDS = ROOT / ".credentials.local"
REMOTE = "/home/mycosoft/mycosoft/mas/.credentials.maps.env"


def load_vm() -> None:
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if line and not line.startswith("#") and "=" not in line:
            continue
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def main() -> None:
    load_vm()
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    pkey = paramiko.Ed25519Key.from_private_key_file(
        str(Path.home() / ".ssh" / "mycosoft_vm_automation_ed25519")
    )
    client.connect(
        "192.168.0.188",
        username="mycosoft",
        pkey=pkey,
        password=password,
        timeout=25,
        allow_agent=False,
        look_for_keys=False,
    )
    stdin, stdout, _stderr = client.exec_command(
        f"sudo -S -p '' install -m 644 {REMOTE} /tmp/itdx_maps_hash.env && echo OK",
        timeout=30,
        get_pty=True,
    )
    stdin.write(password + "\n")
    stdin.flush()
    stdin.channel.shutdown_write()
    print("COPY", stdout.read().decode("utf-8", "replace").replace(password, "***")[-80:])
    dest = Path(tempfile.gettempdir()) / "itdx_188_maps_hash.env"
    sftp = client.open_sftp()
    sftp.get("/tmp/itdx_maps_hash.env", str(dest))
    sftp.close()
    stdin, stdout, _stderr = client.exec_command(
        "sudo -S -p '' rm -f /tmp/itdx_maps_hash.env", timeout=20, get_pty=True
    )
    stdin.write(password + "\n")
    stdin.flush()
    client.close()
    print("188_MAPS")
    for line in dest.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12] if value else "-"
        print(
            f"  {name} len={len(value)} sha256_12={digest} starts_AIza={value.startswith('AIza')}"
        )
    dest.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
