#!/usr/bin/env python3
r"""
Restart Earth-2 API in WSL on 192.168.0.249 (Legion 4080A). Requires
OpenSSH to `owner2@192.168.0.249` (same as scripts/_legion249_portproxy.py):
  %USERPROFILE%\.ssh\id_ed25519

Uses scripts/restart_earth2_wsl_249.sh (LF) piped to:
  wsl -d Ubuntu -u root -- /bin/bash -s
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SH = REPO / "scripts" / "restart_earth2_wsl_249.sh"
HOST = "owner2@192.168.0.249"
REMOTE = "wsl -d Ubuntu -u root -- /bin/bash -s"


def main() -> int:
    if not SH.is_file():
        print("Missing", SH, file=sys.stderr)
        return 2
    raw = SH.read_bytes()
    if b"\r\n" in raw:
        raw = raw.replace(b"\r\n", b"\n")
    p = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST, REMOTE],
        input=raw,
        capture_output=True,
        timeout=120,
    )
    out = p.stdout.decode("utf-8", errors="replace")
    err = p.stderr.decode("utf-8", errors="replace")
    print(out, end="")
    if err.strip():
        print(err, file=sys.stderr, end="")
    return 0 if p.returncode == 0 else p.returncode


if __name__ == "__main__":
    raise SystemExit(main())
