"""Inspect why /api/itdx 404s on 188 after main checkout. No secrets."""

from __future__ import annotations

import os
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]


def load_creds() -> None:
    for line in (ROOT / ".credentials.local").read_text(encoding="utf-8", errors="replace").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def main() -> None:
    load_creds()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key_path = Path.home() / ".ssh" / "mycosoft_vm_automation_ed25519"
    client.connect(
        "192.168.0.188",
        username="mycosoft",
        pkey=paramiko.Ed25519Key.from_private_key_file(str(key_path)),
        password=os.environ.get("VM_PASSWORD") or "",
        timeout=25,
        allow_agent=True,
        look_for_keys=True,
    )
    cmd = r"""
cd /home/mycosoft/mycosoft/mas
echo HEAD $(git rev-parse --short=12 HEAD)
echo WD $(systemctl show mas-orchestrator -p WorkingDirectory --value)
echo EXEC $(systemctl show mas-orchestrator -p ExecStart --value)
grep -n itdx mycosoft_mas/core/myca_main.py | head
echo ---IMPORT---
python3 -c 'from mycosoft_mas.core.routers import itdx_api; print("import_ok", itdx_api.router.prefix)'
echo ---HEALTH---
curl -sS -m 6 -o /tmp/h.txt -w 'health %{http_code}\n' http://127.0.0.1:8001/health
python3 -c 'import json; d=json.load(open("/tmp/h.txt")); print({k:d.get(k) for k in ("status","git_sha","version","commit","revision") if k in d or True})'
echo ---OPENAPI---
curl -sS -m 8 -o /tmp/o.txt -w 'openapi %{http_code}\n' http://127.0.0.1:8001/openapi.json
python3 -c 'import json; d=json.load(open("/tmp/o.txt")); paths=sorted(d.get("paths",{})); print("npaths",len(paths)); print([p for p in paths if "itdx" in p or "fusarium" in p][:50])'
echo ---FUS---
curl -sS -m 5 -o /dev/null -w 'threats %{http_code}\n' http://127.0.0.1:8001/api/fusarium/threats
curl -sS -m 5 -o /dev/null -w 'nlm %{http_code}\n' http://127.0.0.1:8001/api/nlm/health
echo ---JOURNAL---
journalctl -u mas-orchestrator -n 80 --no-pager | grep -Ei 'itdx|Error|Traceback|ImportError' | tail -40
"""
    stdin, stdout, stderr = client.exec_command(cmd, timeout=50)
    print(stdout.read().decode("utf-8", "replace"))
    err = stderr.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[:800])
    client.close()


if __name__ == "__main__":
    main()
