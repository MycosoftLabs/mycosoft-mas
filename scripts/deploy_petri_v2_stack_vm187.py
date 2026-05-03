#!/usr/bin/env python3
"""
Deploy Petri Dish v2 Rust engine (8050) + MyceliumSeg API (8051) on Sandbox VM 187.

Prereqs on 187: git clone of MAS at ~/mycosoft/mas tracking origin/main, Docker installed.

After deploy, set on MAS VM 188 (systemd env or container env):
  PETRI_ENGINE_V2_URL=http://192.168.0.187:8050

Optional: PETRI_SEG_SERVICE_URL=http://192.168.0.187:8051 for website / MAS seg features.

Loads VM_PASSWORD from .credentials.local (MAS repo, WEBSITE/website, or ~/.mycosoft-credentials).
"""
from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("pip install paramiko", file=sys.stderr)
    raise

MAS_ROOT = Path(__file__).resolve().parent.parent
CODE_ROOT = MAS_ROOT.parent.parent


def _load_credentials() -> None:
    for cand in (
        MAS_ROOT / ".credentials.local",
        CODE_ROOT / "WEBSITE" / "website" / ".credentials.local",
        Path.home() / ".mycosoft-credentials",
    ):
        if not cand.is_file():
            continue
        for line in cand.read_text(encoding="utf-8", errors="replace").splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
        return
    sys.exit("No credentials file found for VM SSH")


REMOTE_BASH = textwrap.dedent(
    """
    set -euo pipefail
    MAS_DIR="$HOME/mycosoft/mas"
    SRC_ROOT=""
    CLONE_DIR="/tmp/mas-petri-deploy-$$"

    sync_local_clone() {
      if [ ! -d "$MAS_DIR/.git" ]; then
        return 1
      fi
      cd "$MAS_DIR"
      git fetch origin || true
      if git reset --hard origin/main; then
        SRC_ROOT="$MAS_DIR"
        return 0
      fi
      return 1
    }

    if sync_local_clone; then
      echo "Using MAS repo at $SRC_ROOT"
    else
      echo "=== Shallow clone to $CLONE_DIR (local $MAS_DIR reset failed — often root-owned files; sudo chown -R mycosoft:mycosoft $MAS_DIR to fix) ==="
      rm -rf "$CLONE_DIR"
      git clone --depth 1 https://github.com/MycosoftLabs/mycosoft-mas.git "$CLONE_DIR"
      SRC_ROOT="$CLONE_DIR"
    fi

    echo "=== Build petri_engine ==="
    cd "$SRC_ROOT/services/petri_engine"
    docker build -t mycosoft/petri-engine:v2 .
    docker rm -f petri-engine-v2 2>/dev/null || true
    docker run -d --name petri-engine-v2 --restart unless-stopped -p 8050:8050 \\
      -e PETRI_ENGINE_PORT=8050 mycosoft/petri-engine:v2
    sleep 2
    curl -sS "http://127.0.0.1:8050/health" | head -c 400 || true
    echo ""

    echo "=== Build MyceliumSeg API ==="
    cd "$SRC_ROOT"
    docker build -f scripts/myceliumseg/Dockerfile -t mycosoft/myceliumseg-api:v1 .
    DBURL=""
    if [ -f /opt/mycosoft/.env ]; then
      DBURL=$(grep -E '^MINDEX_DATABASE_URL=' /opt/mycosoft/.env 2>/dev/null | cut -d= -f2- | tr -d '"' || true)
    fi
    docker rm -f myceliumseg-api 2>/dev/null || true
    docker run -d --name myceliumseg-api --restart unless-stopped -p 8051:8051 \\
      -e PORT=8051 \\
      -e MINDEX_DATABASE_URL="${DBURL}" \\
      mycosoft/myceliumseg-api:v1
    sleep 2
    curl -sS "http://127.0.0.1:8051/health" | head -c 400 || echo "(seg health failed — check MINDEX_DATABASE_URL on host .env)"
    echo ""
    echo "Done. Configure MAS 188: PETRI_ENGINE_V2_URL=http://192.168.0.187:8050"
    """
).strip()


def main() -> None:
    _load_credentials()
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    if not pw:
        sys.exit("VM_PASSWORD not set")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("192.168.0.187", username="mycosoft", password=pw, timeout=45)
    stdin, stdout, stderr = client.exec_command("bash -s", timeout=600_000)
    stdin.write(REMOTE_BASH + "\n")
    stdin.channel.shutdown_write()
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    client.close()
    print(out)
    if err.strip():
        print(err, file=sys.stderr)
    if stdout.channel.recv_exit_status() != 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
