"""Install Fusarium Maps key onto 188. Never print key values."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import time
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
CREDS = ROOT / ".credentials.local"
REMOTE_MAPS = "/home/mycosoft/mycosoft/mas/.credentials.maps.env"
REMOTE_DROPIN_DIR = "/etc/systemd/system/mas-orchestrator.service.d"
REMOTE_DROPIN = f"{REMOTE_DROPIN_DIR}/google-maps.conf"
SOURCE_NAME = "FUSARIUM_GOOGLE_MAPS_API_KEY"
OLD_TILES_HASH = "da37efa21333"
ALIAS_NAMES = (
    "GOOGLE_MAPS_API_KEY",
    "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY",
    "GOOGLE_API_KEY",
    "FUSARIUM_GOOGLE_MAPS_API_KEY",
)


def load_fusarium_key() -> str:
    if not CREDS.is_file():
        raise SystemExit("NO_CREDS_FILE")
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() != SOURCE_NAME:
            continue
        value = value.strip().strip('"').strip("'")
        if not value:
            raise SystemExit("FUSARIUM_KEY_EMPTY")
        return value
    raise SystemExit("FUSARIUM_KEY_MISSING")


def load_vm_creds() -> None:
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def connect() -> paramiko.SSHClient:
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
    return client


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 90, use_sudo: bool = False) -> str:
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    if use_sudo:
        cmd = f"sudo -S -p '' {cmd}"
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout, get_pty=use_sudo)
    if use_sudo:
        stdin.write(password + "\n")
        stdin.flush()
        stdin.channel.shutdown_write()
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    if password:
        out = out.replace(password, "***")
        err = err.replace(password, "***")
    return (out + ("\n" + err if err.strip() else "")).replace("\u25cf", "*")


def fingerprint_text(text: str) -> None:
    for line in text.splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if not value:
            continue
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
        print(f"  {name} len={len(value)} prefix={value[:4]} sha256_12={digest}")


def main() -> int:
    key = load_fusarium_key()
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    print("SOURCE", SOURCE_NAME, "len", len(key), "prefix", key[:4], "sha256_12", digest)
    if digest == OLD_TILES_HASH:
        print("ABORT same hash as old tiles key")
        return 3
    load_vm_creds()
    body = "\n".join(f"{name}={key}" for name in ALIAS_NAMES) + "\n"
    dropin = "[Service]\n" f"EnvironmentFile=-{REMOTE_MAPS}\n"
    client = connect()
    tmp = Path(tempfile.gettempdir()) / "itdx_fusarium_maps.env"
    drop_tmp = Path(tempfile.gettempdir()) / "itdx_google-maps.conf"
    verify = Path(tempfile.gettempdir()) / "itdx_188_maps_verify.env"
    try:
        tmp.write_text(body, encoding="utf-8")
        drop_tmp.write_text(dropin, encoding="utf-8")
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        sftp = client.open_sftp()
        sftp.put(str(tmp), "/tmp/credentials.maps.env")
        sftp.put(str(drop_tmp), "/tmp/google-maps.conf")
        sftp.close()
        print(
            run(
                client,
                "bash -lc "
                + repr(
                    f"install -m 600 /tmp/credentials.maps.env {REMOTE_MAPS} && "
                    f"rm -f /tmp/credentials.maps.env && "
                    f"echo MAPS_ENV_INSTALLED && "
                    f"cut -d= -f1 {REMOTE_MAPS}"
                ),
                use_sudo=True,
            )
        )
        print(
            run(
                client,
                "bash -lc "
                + repr(
                    f"mkdir -p {REMOTE_DROPIN_DIR} && "
                    f"install -m 644 /tmp/google-maps.conf {REMOTE_DROPIN} && "
                    "rm -f /tmp/google-maps.conf && "
                    "systemctl daemon-reload && "
                    "systemctl restart mas-orchestrator && "
                    "echo RESTARTED && "
                    "systemctl is-active mas-orchestrator && "
                    "systemctl show mas-orchestrator -p EnvironmentFiles --no-pager"
                ),
                use_sudo=True,
                timeout=120,
            )
        )
        time.sleep(6)
        print(
            "HEALTH",
            run(
                client,
                "curl -sS -m 10 -o /tmp/itdx_h.txt -w '%{http_code}' "
                "http://127.0.0.1:8001/api/itdx/health; echo; "
                "python3 -c \"import json; d=json.load(open('/tmp/itdx_h.txt')); print(d.get('status') or d.get('ok') or list(d)[:6])\"",
                timeout=20,
            ),
        )
        print(
            run(
                client,
                f"install -m 644 {REMOTE_MAPS} /tmp/itdx_maps_verify.env && echo VERIFY_COPIED",
                use_sudo=True,
            )
        )
        sftp = client.open_sftp()
        sftp.get("/tmp/itdx_maps_verify.env", str(verify))
        sftp.close()
        print(run(client, "rm -f /tmp/itdx_maps_verify.env", use_sudo=True))
        print("REMOTE_HASHES")
        fingerprint_text(verify.read_text(encoding="utf-8", errors="replace"))
        remote_hashes = set()
        for line in verify.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" not in line:
                continue
            value = line.split("=", 1)[1].strip()
            if value:
                remote_hashes.add(hashlib.sha256(value.encode("utf-8")).hexdigest()[:12])
        if OLD_TILES_HASH in remote_hashes:
            print("WARN remote still has old tiles hash")
        elif remote_hashes == {digest}:
            print("REMOTE_OK fusarium hash only")
        else:
            print("REMOTE_HASH_SET", ",".join(sorted(remote_hashes)))
    finally:
        for path in (tmp, drop_tmp, verify):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
