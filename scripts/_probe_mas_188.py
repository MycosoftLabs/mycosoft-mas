"""One-shot: probe MAS VM listening ports and meshtastic route (no secrets)."""
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
    if not pw:
        print("no_vm_password")
        return 1
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.188", username="mycosoft", password=pw, timeout=25, allow_agent=False, look_for_keys=False)
    cmds = [
        "docker ps --format '{{.Names}} {{.Status}}'",
        "curl -s -m 5 http://127.0.0.1:8000/openapi.json | head -c 200 || echo curl8000_fail",
        "curl -s -m 5 http://127.0.0.1:8001/openapi.json | head -c 200 || echo curl8001_fail",
        "curl -s -m 5 -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/meshtastic/stats || echo",
        "curl -s -m 5 -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/api/meshtastic/stats || echo",
        "ss -lntp | grep -E ':8000|:8001' || true",
        "systemctl is-active mas-orchestrator 2>/dev/null || true",
    ]
    for cmd in cmds:
        print("---")
        _, out, err = c.exec_command(cmd, timeout=60)
        sys.stdout.write(out.read().decode(errors="replace"))
        sys.stdout.write(err.read().decode(errors="replace"))
    c.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
