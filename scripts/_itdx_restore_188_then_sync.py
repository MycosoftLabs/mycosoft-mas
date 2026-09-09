"""Restore deleted 188 ITDX files, bring :8001 up, then sync to origin/main.

Preserves .env and data/. Never prints secrets.
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
STASH_PATHS = (
    "mycosoft_mas/agents/__init__.py",
    "mycosoft_mas/core/agent_registry.py",
    "mycosoft_mas/core/myca_main.py",
    "mycosoft_mas/core/routers/avani_router.py",
    "mycosoft_mas/core/routers/compliance_api.py",
    "mycosoft_mas/core/routers/fusarium_api.py",
    "mycosoft_mas/core/routers/nlm_api.py",
    "mycosoft_mas/core/routers/psathyrella_api.py",
    "mycosoft_mas/nlm/inference/service.py",
    "mycosoft_mas/security/posture_integrity_monitor.py",
    "mycosoft_mas/compliance/evidence_emitter.py",
    "mycosoft_mas/compliance/evidence_register.py",
    "mycosoft_mas/core/routers/security_evidence_api.py",
    "mycosoft_mas/core/routers/soc_operating_history_api.py",
    "mycosoft_mas/engines/intention/intention_service.py",
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


def wait_8001(client: paramiko.SSHClient, label: str) -> str:
    rows = []
    for i in range(12):
        time.sleep(3 if i else 2)
        body = run(
            client,
            "systemctl is-active mas-orchestrator; "
            "curl -sS -m 5 -o /tmp/itdx_h.txt -w '%{http_code}' "
            "http://127.0.0.1:8001/api/itdx/health || true; echo; "
            "head -c 160 /tmp/itdx_h.txt 2>/dev/null; echo",
            timeout=20,
        )
        rows.append(body)
        if "200" in body and "ITDX" not in body:
            print(label, "TRY", i, "OK")
            print(body)
            return body
        if "200" in body:
            print(label, "TRY", i, "OK")
            print(body)
            return body
        print(label, "TRY", i, body[:220])
    return "\n".join(rows)


def main() -> int:
    load_creds()
    client = connect()
    try:
        restore = run(
            client,
            f"""set -e
cd {REMOTE}
echo HEAD_NOW $(git rev-parse HEAD)
echo BRANCH_NOW $(git rev-parse --abbrev-ref HEAD)
if [ -d /tmp/itdx-188-pre-main ]; then
  cp -a /tmp/itdx-188-pre-main/. {REMOTE}/
  echo RESTORED_PRE_MAIN_BACKUP
  find /tmp/itdx-188-pre-main -type f | sed 's|.*/||'
else
  echo NO_PRE_MAIN_BACKUP
fi
test -f mycosoft_mas/core/routers/itdx_api.py && echo HAS_ITDX_API || echo MISSING_ITDX_API
test -f mycosoft_mas/agents/itdx_task8_agent.py && echo HAS_TASK8 || echo MISSING_TASK8
ls /etc/systemd/system/mas-orchestrator.service.d/ | tr '\\n' ' '; echo
""",
        )
        print("RESTORE")
        print(restore)

        print(
            run(
                client,
                "systemctl restart mas-orchestrator && echo RESTARTED_RESTORE",
                timeout=120,
                use_sudo=True,
            )
        )
        wait_8001(client, "AFTER_RESTORE")

        stash_list = " ".join(STASH_PATHS)
        sync = run(
            client,
            f"""set -e
cd {REMOTE}
mkdir -p /tmp/itdx-188-dirty-stash
for f in {stash_list}; do
  if [ -e "$f" ]; then
    mkdir -p "/tmp/itdx-188-dirty-stash/$(dirname "$f")"
    cp -a "$f" "/tmp/itdx-188-dirty-stash/$f"
    echo STASHED "$f"
  fi
done
# Drop dirty tracked + colliding untracked so checkout can proceed.
git checkout -- {stash_list} 2>/dev/null || true
git clean -f -- mycosoft_mas/compliance/evidence_emitter.py \
  mycosoft_mas/compliance/evidence_register.py \
  mycosoft_mas/core/routers/security_evidence_api.py \
  mycosoft_mas/core/routers/soc_operating_history_api.py \
  mycosoft_mas/engines/intention/intention_service.py \
  mycosoft_mas/agents/itdx_task8_agent.py \
  mycosoft_mas/core/routers/itdx_api.py \
  mycosoft_mas/core/routers/itdx_public_sources.py \
  tests/test_itdx_task8_api.py || true
git fetch origin main
git checkout -B main origin/main
git reset --hard origin/main
echo AFTER_HEAD $(git rev-parse HEAD)
git log -1 --oneline
git status -sb | head -6
test -f mycosoft_mas/core/routers/itdx_api.py && echo HAS_ITDX_API
test -f mycosoft_mas/engines/intention/intention_service.py && echo HAS_INTENTION_SERVICE
test -f mycosoft_mas/agents/itdx_task8_agent.py && echo HAS_TASK8
grep -n itdx_api mycosoft_mas/core/myca_main.py | head
""",
            timeout=180,
        )
        print("SYNC")
        print(sync)
        if TARGET not in sync and TARGET[:12] not in sync:
            print("HEAD_MISMATCH")
            return 4

        print(
            run(
                client,
                "systemctl restart mas-orchestrator && echo RESTARTED_MAIN",
                timeout=120,
                use_sudo=True,
            )
        )
        wait_8001(client, "AFTER_MAIN")
        print(
            run(
                client,
                f"cd {REMOTE} && echo LIVE_HEAD $(git rev-parse --short=12 HEAD) && "
                "echo LIVE_BRANCH $(git rev-parse --abbrev-ref HEAD) && "
                "systemctl is-active mas-orchestrator && "
                "ss -lnt | grep 8001 || true",
            )
        )
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
