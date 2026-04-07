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

    script = r"""set -e
echo "=== Docker Ollama containers ==="
docker ps -a --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null | grep -iE 'ollama|NAME' || true
for name in $(docker ps -a --format '{{.Names}}' 2>/dev/null | grep -i ollama || true); do
  st=$(docker inspect -f '{{.State.Status}}' "$name" 2>/dev/null || echo missing)
  if [ "$st" = "exited" ] || [ "$st" = "created" ]; then
    echo "Starting container: $name"
    docker start "$name" || true
  fi
done
sleep 2
echo "=== GET /api/tags (native Ollama) ==="
curl -sS -m 8 http://127.0.0.1:11434/api/tags 2>&1 | head -c 2000 || echo "FAIL_11434"
echo ""
echo "=== GET /v1/models (OpenAI compat for MYCA) ==="
curl -sS -m 8 http://127.0.0.1:11434/v1/models 2>&1 | head -c 2000 || echo "FAIL_V1"
echo ""
"""
    _, out, err = c.exec_command(f"bash -lc {repr(script)}", timeout=120)
    stdout = out.read().decode("utf-8", "replace")
    stderr = err.read().decode("utf-8", "replace")
    print(stdout)
    if stderr.strip():
        print("stderr:", stderr[:800])
    c.close()


if __name__ == "__main__":
    main()
