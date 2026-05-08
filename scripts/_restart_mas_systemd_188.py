"""Git pull on MAS VM and restart systemd mas-orchestrator (source of truth on 8001)."""
import base64
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
    sudo_stdin = base64.b64encode(pw.encode()).decode("ascii")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.188", username="mycosoft", password=pw, timeout=30, allow_agent=False, look_for_keys=False)
    script = f"""
set -e
cd /home/mycosoft/mycosoft/mas
git fetch origin
git reset --hard origin/main
git log -1 --oneline
echo {sudo_stdin} | base64 -d | sudo -S systemctl restart mas-orchestrator
sleep 8
curl -s -o /dev/null -w "meshtastic_stats_http=%{{http_code}}\\n" http://127.0.0.1:8001/api/meshtastic/stats
curl -s http://127.0.0.1:8001/openapi.json | python3 -c "import json,sys; p=json.load(sys.stdin); print('meshtastic_in_openapi', any('meshtastic' in k for k in p.get('paths',{{}})))"
"""
    _, o, e = c.exec_command(script, timeout=180)
    sys.stdout.write(o.read().decode(errors="replace"))
    sys.stdout.write(e.read().decode(errors="replace"))
    c.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
