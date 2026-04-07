"""Start Ollama on MAS VM 188 if stopped; verify OpenAI-compatible /v1 API (MYCA Nemotron default).

Loads VM credentials from .credentials.local (same as other deploy scripts).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

REPO = Path(__file__).resolve().parent.parent


def load_creds() -> str:
    p = REPO / ".credentials.local"
    for line in p.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    if not pw:
        raise SystemExit("No VM_PASSWORD / VM_SSH_PASSWORD in .credentials.local")
    return pw


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pw = load_creds()
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.188", username="mycosoft", password=pw, timeout=45)

    script = r"""
set -e
echo "=== Docker: containers matching ollama ==="
docker ps -a 2>/dev/null | grep -i ollama || true
for id in $(docker ps -aq --filter name=ollama 2>/dev/null); do
  echo "docker start $id"
  docker start "$id" 2>/dev/null || true
done
sleep 2
echo "=== GET /api/tags (native Ollama) ==="
curl -sS -m 8 http://127.0.0.1:11434/api/tags 2>&1 | head -c 2000 || echo "curl_tags_failed"
echo ""
echo "=== GET /v1/models (OpenAI compat for MYCA) ==="
curl -sS -m 8 http://127.0.0.1:11434/v1/models 2>&1 | head -c 2000 || echo "curl_v1_failed"
echo ""
"""
    stdin, stdout, stderr = c.exec_command("bash -s", timeout=120)
    stdin.write(script.encode("utf-8"))
    stdin.close()
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    print(out)
    if err.strip():
        print("stderr:", err[:800])
    c.close()


if __name__ == "__main__":
    main()
