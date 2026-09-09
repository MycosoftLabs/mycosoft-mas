"""Copy ITDX Task 8 router onto MAS 188 and restart mas-orchestrator. No secrets printed."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "mycosoft_mas/agents/itdx_task8_agent.py",
    "mycosoft_mas/core/routers/itdx_api.py",
    "mycosoft_mas/core/routers/itdx_public_sources.py",
    "mycosoft_mas/core/routers/avani_router.py",
    "mycosoft_mas/core/routers/nlm_api.py",
    "mycosoft_mas/nlm/inference/service.py",
    "mycosoft_mas/engines/intention/intention_service.py",
    "mycosoft_mas/core/myca_main.py",
    "mycosoft_mas/agents/__init__.py",
    "mycosoft_mas/core/agent_registry.py",
    "tests/test_itdx_task8_api.py",
]


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
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        host,
        username="mycosoft",
        password=password,
        timeout=25,
        allow_agent=True,
        look_for_keys=True,
    )
    return client


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 60) -> str:
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    return (out + ("\n" + err if err.strip() else "")).replace("\u25cf", "*")


def main() -> int:
    load_creds()
    client = connect()
    try:
        discover = run(
            client,
            "systemctl is-active mas-orchestrator; "
            "systemctl show mas-orchestrator -p FragmentPath -p WorkingDirectory -p ExecStart --no-pager; "
            "ls -d /home/mycosoft/mycosoft/mas /home/mycosoft/mycosoft-mas /opt/mycosoft/mas /home/mycosoft/mas 2>/dev/null; "
            "ss -lnt | grep 8001 || true; "
            "ps -C python,python3 -o pid,cmd --no-headers 2>/dev/null | head -20",
        )
        print(discover)

        remote_root = None
        for candidate in (
            "/home/mycosoft/mycosoft/mas",
            "/home/mycosoft/mycosoft-mas",
            "/opt/mycosoft/mas",
            "/home/mycosoft/mas",
        ):
            check = run(client, f"test -f {candidate}/mycosoft_mas/core/myca_main.py && echo YES || echo NO")
            if "YES" in check:
                remote_root = candidate
                break
        if not remote_root:
            print("NO_REMOTE_ROOT")
            return 3
        print("REMOTE_ROOT", remote_root)

        sftp = client.open_sftp()
        for rel in FILES:
            local = ROOT / rel
            remote = f"{remote_root}/{rel}"
            remote_dir = str(Path(remote).parent).replace("\\", "/")
            run(client, f"mkdir -p {remote_dir}")
            sftp.put(str(local), remote)
            print("PUT", rel)
        sftp.close()

        restart = run(
            client,
            "sudo -n systemctl restart mas-orchestrator && echo RESTARTED_NOPASS || echo NEED_SUDO_PASS",
            timeout=90,
        )
        print(restart)
        if "NEED_SUDO_PASS" in restart:
            password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
            stdin, stdout, stderr = client.exec_command(
                "sudo -S -p '' systemctl restart mas-orchestrator && echo RESTARTED_SUDO",
                timeout=90,
            )
            stdin.write(password + "\n")
            stdin.flush()
            stdin.channel.shutdown_write()
            print(stdout.read().decode("utf-8", "replace"))
            err = stderr.read().decode("utf-8", "replace")
            print(err.replace(password, "***")[:400])

        health = run(
            client,
            "sleep 3; curl -sS -m 8 -o /tmp/itdx_h.txt -w '%{http_code}' http://127.0.0.1:8001/api/itdx/health; echo; "
            "head -c 300 /tmp/itdx_h.txt; echo; "
            "systemctl is-active mas-orchestrator",
            timeout=40,
        )
        print("LOCAL_HEALTH", health)
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
