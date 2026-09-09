"""Force 188 onto origin/main. Keep :8001 up if checkout fails.

Never print secrets. Restart orchestrator only after HEAD is target main.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
TARGET = "a34b66a039baf8c9b1e3812bb21bda753ef0167b"
REMOTE = "/home/mycosoft/mycosoft/mas"


def load_creds() -> None:
    creds = ROOT / ".credentials.local"
    if not creds.exists():
        return
    for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def connect() -> paramiko.SSHClient:
    host = os.environ.get("MAS_VM_HOST") or os.environ.get("MAS_VM_IP") or "192.168.0.188"
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    key_path = Path.home() / ".ssh" / "mycosoft_vm_automation_ed25519"
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kwargs = {
        "hostname": host,
        "username": "mycosoft",
        "timeout": 30,
        "allow_agent": True,
        "look_for_keys": True,
    }
    if key_path.exists():
        kwargs["pkey"] = paramiko.Ed25519Key.from_private_key_file(str(key_path))
    if password:
        kwargs["password"] = password
    client.connect(**kwargs)
    return client


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 180, use_sudo: bool = False) -> str:
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
    load_creds()
    client = connect()
    try:
        inspect = run(
            client,
            f"""cd {REMOTE}
echo HEAD $(git rev-parse HEAD)
echo BRANCH $(git rev-parse --abbrev-ref HEAD)
git status --porcelain | head -30
echo '---SKIP-WORKTREE---'
git ls-files -v | awk '$1 ~ /[a-zS]/ {{print}}' | head
echo '---ITDX---'
test -f mycosoft_mas/core/routers/itdx_api.py && echo HAS_ITDX || echo MISSING_ITDX
curl -sS -m 5 -o /dev/null -w 'PRE_HTTP %{{http_code}}\\n' http://127.0.0.1:8001/api/itdx/health || true
""",
        )
        print("INSPECT")
        print(inspect)

        sync = run(
            client,
            f"""set -e
cd {REMOTE}
# Keep a copy of still-present hot files.
mkdir -p /tmp/itdx-188-force-backup
cp -a mycosoft_mas/core/myca_main.py /tmp/itdx-188-force-backup/ 2>/dev/null || true
# Discard tracked dirt on the CMMC branch only.
git reset --hard HEAD
git status --porcelain | awk '/^\\?\\?/{{print}}' | head -20
# Checkout main. Untracked data/ and .env stay.
git checkout -B main origin/main
echo AFTER_HEAD $(git rev-parse HEAD)
echo AFTER_BRANCH $(git rev-parse --abbrev-ref HEAD)
git log -1 --oneline
test -f mycosoft_mas/core/routers/itdx_api.py && echo HAS_ITDX_API
test -f mycosoft_mas/engines/intention/intention_service.py && echo HAS_INTENTION_SERVICE
test -f mycosoft_mas/agents/itdx_task8_agent.py && echo HAS_TASK8
grep -n 'itdx_api\\|include_router' mycosoft_mas/core/myca_main.py | head -20
""",
            timeout=180,
        )
        print("SYNC")
        print(sync)
        if TARGET not in sync and TARGET[:12] not in sync:
            print("HEAD_MISMATCH — leave orchestrator on previous process")
            # Restore ITDX hot files so a later restart still works.
            print(
                run(
                    client,
                    f"""cd {REMOTE}
if [ ! -f mycosoft_mas/core/routers/itdx_api.py ] && [ -d /tmp/itdx-188-pre-main ]; then
  cp -a /tmp/itdx-188-pre-main/. {REMOTE}/
  echo RESTORED_HOT_ITDX
fi
""",
                )
            )
            return 4

        print(
            run(
                client,
                "systemctl restart mas-orchestrator && echo RESTARTED_MAIN",
                timeout=120,
                use_sudo=True,
            )
        )
        ok = False
        for i in range(16):
            time.sleep(3)
            body = run(
                client,
                "systemctl is-active mas-orchestrator; "
                "curl -sS -m 6 -o /tmp/itdx_h.txt -w '%{http_code}' "
                "http://127.0.0.1:8001/api/itdx/health || true; echo; "
                "head -c 180 /tmp/itdx_h.txt 2>/dev/null; echo",
                timeout=20,
            )
            print("WAIT", i, body[:240])
            if "\n200\n" in f"\n{body}" or body.strip().startswith("active\n200"):
                ok = True
                break
            if "200" in body and "healthy" in body:
                ok = True
                break
        print("HEALTH_OK" if ok else "HEALTH_WAIT_TIMEOUT")
        print(
            run(
                client,
                f"cd {REMOTE} && echo LIVE_HEAD $(git rev-parse HEAD) && "
                "echo LIVE_BRANCH $(git rev-parse --abbrev-ref HEAD) && "
                "ss -lnt | grep 8001 || true && "
                "journalctl -u mas-orchestrator -n 25 --no-pager | tail -25",
                timeout=30,
            )
        )
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
