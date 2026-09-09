"""Inspect 188 :8200 NLM and process map. No secrets."""

from __future__ import annotations

import os
from pathlib import Path

import paramiko

CREDS = Path(__file__).resolve().parents[1] / ".credentials.local"
KEYS = [
    Path.home() / ".ssh" / "mycosoft_vm_ed25519",
    Path.home() / ".ssh" / "mycosoft_vm_automation_ed25519",
    Path.home() / ".ssh" / "id_ed25519",
]


def load_creds() -> None:
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip() or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def main() -> None:
    load_creds()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key = next(p for p in KEYS if p.exists())
    client.connect(
        "192.168.0.188",
        username="mycosoft",
        key_filename=str(key),
        timeout=15,
        allow_agent=False,
        look_for_keys=False,
    )
    cmd = r"""
set +e
echo '=== 8200 endpoints ==='
for p in /health / /docs /openapi.json /api/nlm/health /predict /api/predict /v1/models /status /model /ready; do
  code=$(curl -sS -m 3 -o /tmp/nbody.txt -w '%{http_code}' "http://127.0.0.1:8200$p")
  echo "$code $p $(head -c 180 /tmp/nbody.txt | tr '\n' ' ')"
done
echo '=== listen 8200 ==='
ss -lptn | grep 8200 || netstat -lptn 2>/dev/null | grep 8200
echo '=== systemd nlm ==='
systemctl list-units --type=service --all | grep -Ei 'nlm|llama|ollama' || true
echo '=== process ==='
ps aux | grep -Ei '8200|nlm' | grep -v grep | head
echo '=== docker 8200 ==='
docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep 8200 || true
"""
    stdin, stdout, stderr = client.exec_command(cmd, timeout=40)
    print(stdout.read().decode("utf-8", "replace"))
    err = stderr.read().decode("utf-8", "replace")
    if err.strip():
        print("STDERR", err[:800])
    client.close()


if __name__ == "__main__":
    main()
