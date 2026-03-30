#!/usr/bin/env python3
"""SSH to MAS VM 188: diagnose myca-orchestrator-new, fix, verify localhost health."""
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for line in (REPO_ROOT / ".credentials.local").read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

password = os.environ.get("VM_SSH_PASSWORD") or os.environ.get("VM_PASSWORD")
if not password:
    print("ERROR: no VM password in env / .credentials.local")
    sys.exit(1)

import paramiko

HOST = "192.168.0.188"
USER = "mycosoft"


def main() -> int:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting {USER}@{HOST}...")
    client.connect(HOST, username=USER, password=password, timeout=45)

    def run(cmd: str, timeout: int = 180) -> tuple[int, str, str]:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        code = stdout.channel.recv_exit_status()
        return code, out, err

    print("\n--- docker ps (MAS-related) ---")
    _, o, e = run("docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>&1 | head -25")
    print(o)
    if e.strip():
        print("stderr:", e[:1500])

    print("\n--- inspect myca-orchestrator-new ---")
    code, o, e = run(
        "docker inspect myca-orchestrator-new --format "
        "'status={{.State.Status}} exit={{.State.ExitCode}} err={{.State.Error}}' 2>&1"
    )
    print(o.strip() or "(no output)", "exit", code)

    print("\n--- last 100 log lines ---")
    _, o, _ = run("docker logs myca-orchestrator-new --tail 100 2>&1")
    print(o[-12000:] if len(o) > 12000 else o)

    print("\n--- curl from VM to 127.0.0.1:8001/health ---")
    _, o, e = run("curl -sS -m 10 http://127.0.0.1:8001/health 2>&1 || true")
    print(o.strip() or "(empty)")
    if e.strip():
        print("curl stderr:", e[:500])

    print("\n--- listeners on 8001 ---")
    _, o, _ = run("ss -tlnp 2>/dev/null | grep 8001 || netstat -tlnp 2>/dev/null | grep 8001 || echo none")
    print(o.strip())

    state_cmd = "docker inspect myca-orchestrator-new --format '{{.State.Status}}' 2>/dev/null"
    _, st, _ = run(state_cmd)
    status = (st or "").strip()

    if status in ("exited", "dead", "created"):
        print(f"\n--- container status={status!r}: starting ---")
        run("docker start myca-orchestrator-new 2>&1")
        time.sleep(8)
        _, o, _ = run("docker logs myca-orchestrator-new --tail 40 2>&1")
        print(o)

    if status == "restarting":
        print("\n--- restarting loop: stop/rm and recreate from same image ---")
        run(
            "docker stop myca-orchestrator-new 2>/dev/null; "
            "docker rm myca-orchestrator-new 2>/dev/null; "
            "docker run -d --name myca-orchestrator-new --restart unless-stopped "
            "-p 8001:8000 --env-file /home/mycosoft/mycosoft/mas/.env "
            "mycosoft/mas-agent:latest 2>&1"
        )
        time.sleep(12)
        _, o, _ = run("docker logs myca-orchestrator-new --tail 60 2>&1")
        print(o)

    _, st2, _ = run(state_cmd)
    if (st2 or "").strip() not in ("running",):
        print("\n--- still not running; attempt recreate (image exists) ---")
        run(
            "docker stop myca-orchestrator-new 2>/dev/null || true; "
            "docker rm myca-orchestrator-new 2>/dev/null || true; "
            "docker run -d --name myca-orchestrator-new --restart unless-stopped "
            "-p 8001:8000 --env-file /home/mycosoft/mycosoft/mas/.env "
            "mycosoft/mas-agent:latest 2>&1"
        )
        time.sleep(15)
        _, o, _ = run("docker logs myca-orchestrator-new --tail 80 2>&1")
        print(o)

    print("\n--- final curl 127.0.0.1:8001/health ---")
    _, o, _ = run("curl -sS -m 15 http://127.0.0.1:8001/health 2>&1 || true")
    body = o.strip()
    print(body[:500] if body else "(empty — still failing)")
    ok = "healthy" in body.lower() or '"status"' in body.lower() and "ok" in body.lower()

    client.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
