"""Copy existing Maps-looking key onto 188 mas-orchestrator env. Never print values."""

from __future__ import annotations

import os
import stat
import sys
import tempfile
import time
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
WEB_ENV = Path(r"D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.env.local")
CREDS = ROOT / ".credentials.local"
REMOTE_MAPS = "/home/mycosoft/mycosoft/mas/.credentials.maps.env"
REMOTE_DROPIN_DIR = "/etc/systemd/system/mas-orchestrator.service.d"
REMOTE_DROPIN = f"{REMOTE_DROPIN_DIR}/google-maps.conf"
ALIAS_NAMES = (
    "GOOGLE_MAPS_API_KEY",
    "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY",
    "GOOGLE_API_KEY",
    "NEXT_PUBLIC_GOOGLE_MAP_TILES_API_KEY",
)


def _parse_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        name, value = text.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name and value:
            out[name] = value
    return out


def _upsert_local_aliases(maps_key: str) -> None:
    existing = CREDS.read_text(encoding="utf-8", errors="replace") if CREDS.is_file() else ""
    lines = existing.splitlines()
    present = set()
    for line in lines:
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        present.add(text.split("=", 1)[0].strip())
    additions = [name for name in ALIAS_NAMES if name not in present]
    if not additions:
        print("LOCAL_CREDS aliases already present (names only)")
        return
    with CREDS.open("a", encoding="utf-8") as handle:
        if existing and not existing.endswith("\n"):
            handle.write("\n")
        handle.write("# Google Maps aliases (gitignored; values never logged)\n")
        for name in additions:
            handle.write(f"{name}={maps_key}\n")
    print("LOCAL_CREDS added names:", ",".join(additions))


def load_creds() -> None:
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def connect() -> paramiko.SSHClient:
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        "192.168.0.188",
        username="mycosoft",
        password=password,
        timeout=25,
        allow_agent=True,
        look_for_keys=True,
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


def main() -> int:
    web = _parse_env(WEB_ENV)
    mas = _parse_env(CREDS)
    maps_key = (
        web.get("NEXT_PUBLIC_GOOGLE_MAP_TILES_API_KEY")
        or web.get("NEXT_PUBLIC_GOOGLE_MAPS_API_KEY")
        or web.get("GOOGLE_MAPS_API_KEY")
        or mas.get("GOOGLE_MAPS_API_KEY")
        or ""
    )
    if not maps_key:
        print("NO_MAPS_KEY_FOUND")
        return 2
    prefix = maps_key[:4] if len(maps_key) >= 4 else "NONE"
    print(f"SOURCE_VAR=NEXT_PUBLIC_GOOGLE_MAP_TILES_API_KEY PREFIX={prefix} LEN={len(maps_key)}")
    _upsert_local_aliases(maps_key)
    load_creds()

    body = "\n".join(f"{name}={maps_key}" for name in ALIAS_NAMES) + "\n"
    dropin = (
        "[Service]\n"
        f"EnvironmentFile=-{REMOTE_MAPS}\n"
    )
    client = connect()
    try:
        show = run(
            client,
            "systemctl show mas-orchestrator -p EnvironmentFiles -p FragmentPath --no-pager; "
            "ls -l /etc/systemd/system/mas-orchestrator.service.d 2>/dev/null || true",
        )
        print("UNIT", show.strip()[:800])

        tmp = Path(tempfile.gettempdir()) / "itdx_credentials.maps.env"
        drop_tmp = Path(tempfile.gettempdir()) / "itdx_google-maps.conf"
        tmp.write_text(body, encoding="utf-8")
        drop_tmp.write_text(dropin, encoding="utf-8")
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        sources = ROOT / "mycosoft_mas/core/routers/itdx_public_sources.py"
        try:
            sftp = client.open_sftp()
            sftp.put(str(tmp), "/tmp/credentials.maps.env")
            sftp.put(str(drop_tmp), "/tmp/google-maps.conf")
            sftp.put(str(sources), "/home/mycosoft/mycosoft/mas/mycosoft_mas/core/routers/itdx_public_sources.py")
            print("PUT itdx_public_sources.py")
            sftp.close()
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            try:
                drop_tmp.unlink(missing_ok=True)
            except OSError:
                pass

        print(
            run(
                client,
                "bash -lc "
                + repr(
                    f"install -m 600 /tmp/credentials.maps.env {REMOTE_MAPS} && "
                    f"rm -f /tmp/credentials.maps.env && "
                    f"test -f {REMOTE_MAPS} && echo MAPS_ENV_INSTALLED && "
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
        time.sleep(5)
        print(
            "HEALTH",
            run(
                client,
                "curl -sS -m 8 -o /tmp/itdx_h.txt -w '%{http_code}' "
                "http://127.0.0.1:8001/api/itdx/health; echo; "
                "head -c 200 /tmp/itdx_h.txt; echo",
                timeout=20,
            ),
        )
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
