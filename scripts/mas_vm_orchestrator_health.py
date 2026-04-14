"""SSH to MAS VM: check orchestrator /health; restart systemd unit if unhealthy. Reads VM_SSH_PASSWORD from .credentials.local."""
from __future__ import annotations

import re
import shlex
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("pip install paramiko", file=sys.stderr)
    sys.exit(1)

REPO = Path(__file__).resolve().parents[1]
CRED = REPO / ".credentials.local"
MAS_IP = "192.168.0.188"
USER = "mycosoft"


def load_vm_password() -> str:
    if not CRED.is_file():
        raise SystemExit(f"Missing {CRED}")
    text = CRED.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        m = re.match(r"^\s*VM_SSH_PASSWORD\s*=\s*(.+)\s*$", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    raise SystemExit("VM_SSH_PASSWORD not found in .credentials.local")


def main() -> None:
    pw = load_vm_password()
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(MAS_IP, username=USER, password=pw, timeout=20)

    def run(cmd: str) -> tuple[int, str, str]:
        _, out, err = c.exec_command(cmd, timeout=90)
        o = out.read().decode("utf-8", errors="replace")
        e = err.read().decode("utf-8", errors="replace")
        code = out.channel.recv_exit_status()
        return code, o, e

    code, o, e = run(
        "curl -sS --connect-timeout 3 --max-time 8 -o /dev/null -w '%{http_code}' "
        "http://127.0.0.1:8001/health 2>/dev/null || echo FAIL"
    )
    print("health_http_code", o.strip())
    if o.strip() in ("200", "204"):
        print("MAS orchestrator OK")
        c.close()
        return

    print("Restarting mas-orchestrator...")
    pwq = shlex.quote(pw)
    rcmd = (
        f"echo {pwq} | sudo -S -k systemctl restart mas-orchestrator; "
        "sleep 4; curl -sS --connect-timeout 3 --max-time 8 -o /dev/null -w '%{http_code}' "
        "http://127.0.0.1:8001/health 2>/dev/null || echo FAIL"
    )
    code, _, e = run(rcmd)
    print("restart_pipeline_stderr", e.strip()[:200])

    _, o2, e2 = run("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/health || true")
    print("health_after", o2.strip(), e2.strip())
    c.close()


if __name__ == "__main__":
    main()
