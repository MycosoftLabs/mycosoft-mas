"""Inspect MAS 188: systemd vs docker, ports, meshtastic path."""
import os
import sys
from pathlib import Path

import paramiko

def load_creds() -> None:
    for p in [
        Path(__file__).resolve().parent.parent / ".credentials.local",
        Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.credentials.local"),
    ]:
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

def main() -> int:
    load_creds()
    pw = (os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or "").strip()
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.188", username="mycosoft", password=pw, timeout=25, allow_agent=False, look_for_keys=False)
    script = r"""
set -e
echo "=== systemctl mas-orchestrator ==="
systemctl is-active mas-orchestrator 2>/dev/null || true
systemctl show mas-orchestrator -p FragmentPath 2>/dev/null || true
echo "=== docker ==="
docker ps -a --filter name=myca-orchestrator-new --format '{{.Status}}'
docker logs myca-orchestrator-new --tail 15 2>&1 || true
echo "=== listeners ==="
ss -lntp | grep -E ':8000|:8001' || true
echo "=== curl meshtastic 8001 ==="
curl -s -o /tmp/m.out -w "%{http_code}" http://127.0.0.1:8001/api/meshtastic/stats; echo; head -c 200 /tmp/m.out; echo
echo "=== openapi grep meshtastic 8001 ==="
curl -s http://127.0.0.1:8001/openapi.json | grep -o meshtastic | head -3 || echo no_match
"""
    _, o, e = c.exec_command(script, timeout=120)
    sys.stdout.write(o.read().decode(errors="replace"))
    sys.stdout.write(e.read().decode(errors="replace"))
    c.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
