"""Sync MAS 188 git working tree to origin/main. Preserve .env and data/.

Never print secrets. Restart mas-orchestrator only when HEAD or hot files change.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
TARGET = "a34b66a039baf8c9b1e3812bb21bda753ef0167b"
REMOTE = "/home/mycosoft/mycosoft/mas"
COLLIDE = (
    "mycosoft_mas/agents/itdx_task8_agent.py",
    "mycosoft_mas/core/routers/itdx_api.py",
    "mycosoft_mas/core/routers/itdx_public_sources.py",
    "mycosoft_mas/engines/intention/intention_service.py",
    "tests/test_itdx_task8_api.py",
)


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


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 120, use_sudo: bool = False) -> str:
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
        before = run(
            client,
            f"cd {REMOTE} && git rev-parse HEAD && git status -sb | head -5 && "
            "test -f /etc/systemd/system/mas-orchestrator.service.d/override.conf && "
            "echo HAS_SKIP_DROPIN || echo NO_SKIP_DROPIN",
        )
        print("BEFORE")
        print(before)

        collide = " ".join(COLLIDE)
        fetch = run(
            client,
            f"""set -e
cd {REMOTE}
git fetch origin main
echo FETCH_MAIN $(git rev-parse origin/main)
mkdir -p /tmp/itdx-188-pre-main
for f in {collide}; do
  if [ -e "$f" ]; then
    mkdir -p "/tmp/itdx-188-pre-main/$(dirname "$f")"
    cp -a "$f" "/tmp/itdx-188-pre-main/$f"
  fi
done
# Untracked files that exist on origin/main would block checkout.
for f in {collide}; do
  if [ -e "$f" ] && git cat-file -e "origin/main:$f" 2>/dev/null; then
    rm -f "$f"
    echo REMOVED_UNTRACKED_FOR_CHECKOUT "$f"
  fi
done
git checkout -B main origin/main
git reset --hard origin/main
echo AFTER_HEAD $(git rev-parse HEAD)
git log -1 --oneline
git status -sb | head -8
test -f mycosoft_mas/engines/intention/intention_service.py && echo HAS_INTENTION_SERVICE
test -f mycosoft_mas/core/routers/itdx_api.py && echo HAS_ITDX_API
test -f mycosoft_mas/agents/itdx_task8_agent.py && echo HAS_TASK8
""",
            timeout=180,
        )
        print("SYNC")
        print(fetch)

        after_head = ""
        for line in fetch.splitlines():
            if line.startswith("AFTER_HEAD "):
                after_head = line.split()[-1]
        need_restart = TARGET[:12] in fetch or (after_head and after_head.startswith(TARGET[:12]))
        if TARGET[:12] not in fetch and TARGET not in fetch:
            print("HEAD_MISMATCH_WANT", TARGET)
            return 4

        skip = run(
            client,
            "grep -n MAS_SKIP_BACKGROUND_STARTUP "
            "/etc/systemd/system/mas-orchestrator.service.d/*.conf 2>/dev/null | "
            "sed 's/=.*/=SET/' || echo NO_SKIP_LINE",
        )
        print("SKIP_STARTUP")
        print(skip)

        if need_restart:
            print(
                run(
                    client,
                    "systemctl restart mas-orchestrator && echo RESTARTED && sleep 4 && "
                    "systemctl is-active mas-orchestrator && "
                    "curl -sS -m 8 -o /tmp/itdx_h.txt -w 'ITDX_HEALTH %{http_code}\\n' "
                    "http://127.0.0.1:8001/api/itdx/health && head -c 220 /tmp/itdx_h.txt && echo",
                    timeout=150,
                    use_sudo=True,
                )
            )
        else:
            print("NO_RESTART")
        print(
            run(
                client,
                f"cd {REMOTE} && echo LIVE_HEAD $(git rev-parse HEAD) && "
                "curl -sS -m 6 -o /tmp/mas_h.txt -w 'MAS_HEALTH %{http_code}\\n' "
                "http://127.0.0.1:8001/health && python3 -c "
                "\"import json; d=json.load(open('/tmp/mas_h.txt')); "
                "print('status',d.get('status')); print('git',d.get('git_sha') or d.get('version') or d.get('commit') or 'none')\" "
                "2>/dev/null || head -c 180 /tmp/mas_h.txt; echo",
                timeout=30,
            )
        )
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
