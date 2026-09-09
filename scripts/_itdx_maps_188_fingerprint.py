"""Fingerprint 188 maps env names/hashes. Never print key values."""

from __future__ import annotations

import os
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
CREDS = ROOT / ".credentials.local"


def load_creds() -> None:
    if not CREDS.is_file():
        return
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


def run(client: paramiko.SSHClient, cmd: str, use_sudo: bool = False) -> str:
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    if use_sudo:
        cmd = f"sudo -S -p '' {cmd}"
    stdin, stdout, stderr = client.exec_command(cmd, timeout=40, get_pty=use_sudo)
    if use_sudo:
        stdin.write(password + "\n")
        stdin.flush()
        stdin.channel.shutdown_write()
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    if password:
        out = out.replace(password, "***")
        err = err.replace(password, "***")
    return out + (("\n" + err) if err.strip() else "")


def main() -> None:
    load_creds()
    client = connect()
    try:
        script = r"""
python3 - <<'PY'
import hashlib
from pathlib import Path
paths = [
    Path("/home/mycosoft/mycosoft/mas/.credentials.maps.env"),
    Path("/home/mycosoft/mycosoft/mas/.credentials.local"),
    Path("/home/mycosoft/mycosoft/mas/.env"),
    Path("/etc/mycosoft/mas-compliance.env"),
]
needles = ("GOOGLE", "FUSARIUM", "GEMINI", "MAPS", "MAP_TILES")
for path in paths:
    print("FILE", path.exists(), path)
    if not path.exists():
        continue
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print("  READ_FAIL", type(exc).__name__)
        continue
    for line in text.splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if not value or not any(n in name.upper() for n in needles):
            continue
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
        print(f"  {name} len={len(value)} prefix={value[:4]} sha256_12={digest}")
PY
"""
        print("AS_USER")
        print(run(client, "bash -lc " + repr(script)))
        print("AS_SUDO")
        print(run(client, "bash -lc " + repr(script), use_sudo=True))
        print(
            "LS",
            run(
                client,
                "bash -lc "
                + repr(
                    "ls -l --time-style=long-iso /home/mycosoft/mycosoft/mas/.credentials.maps.env "
                    "/home/mycosoft/mycosoft/mas/.credentials.local "
                    "/home/mycosoft/mycosoft/mas/.env 2>&1; "
                    "systemctl show mas-orchestrator -p EnvironmentFiles --no-pager"
                ),
                use_sudo=True,
            ),
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
