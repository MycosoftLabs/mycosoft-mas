"""One-shot: MAS journal + import test on 188; MINDEX api rebuild on 189."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import paramiko

# UTF-8 on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
for line in (ROOT / ".credentials.local").read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

PW = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""


def sudo_exec(client: paramiko.SSHClient, cmd: str, timeout: float = 120) -> tuple[int, str, str]:
    ch = client.get_transport().open_session()
    ch.get_pty()
    ch.exec_command("sudo -S " + cmd)
    ch.send(PW + "\n")
    out = err = b""
    t0 = time.time()
    while time.time() - t0 < timeout:
        if ch.recv_ready():
            out += ch.recv(65536)
        if ch.recv_stderr_ready():
            err += ch.recv_stderr(65536)
        if ch.exit_status_ready():
            break
        time.sleep(0.05)
    while ch.recv_ready():
        out += ch.recv(65536)
    while ch.recv_stderr_ready():
        err += ch.recv_stderr(65536)
    code = ch.recv_exit_status() if ch.exit_status_ready() else -1
    return code, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")


def exec_plain(client: paramiko.SSHClient, cmd: str, timeout: float = 600) -> tuple[int, str, str]:
    _, stdout, stderr = client.exec_command(cmd, timeout=int(timeout) + 30)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    return stdout.channel.recv_exit_status(), out, err


def main() -> None:
    # --- MAS 188 ---
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.188", username="mycosoft", password=PW, timeout=45)

    code, jo, je = sudo_exec(c, "journalctl -u mas-orchestrator -n 80 --no-pager", timeout=90)
    print("=== journal mas-orchestrator (last 80) exit", code, "===")
    blob = (jo + je)[-8000:]
    print(blob)

    import_cmd = (
        "cd /home/mycosoft/mycosoft/mas && "
        "timeout 120 ./venv/bin/python -c "
        "'print(\"import_begin\"); import mycosoft_mas.core.myca_main; print(\"import_ok\")' 2>&1"
    )
    code2, o2, e2 = exec_plain(c, import_cmd, timeout=150)
    print("=== MAS import test exit", code2, "===")
    print((o2 + e2)[-5000:])
    c.close()

    # --- MINDEX 189 ---
    c2 = paramiko.SSHClient()
    c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c2.connect("192.168.0.189", username="mycosoft", password=PW, timeout=45)
    # --no-deps: do not recreate db/redis; existing mindex-postgres name conflicts if compose
    # tries to "create" db while an identical-named container already runs.
    mcmd = (
        "cd /home/mycosoft/mindex && docker compose stop api && docker compose rm -f api && "
        "docker compose build --no-cache api && docker compose up -d --no-deps api"
    )
    code3, o3, e3 = exec_plain(c2, mcmd, timeout=900)
    print("=== MINDEX docker api rebuild exit", code3, "===")
    print((o3 + e3)[-6000:])

    time.sleep(8)
    code4, h, _ = exec_plain(c2, "curl -s http://127.0.0.1:8000/health", timeout=30)
    print("=== MINDEX /health exit", code4, "===")
    print(h.strip()[:500])

    c2.close()


if __name__ == "__main__":
    main()
