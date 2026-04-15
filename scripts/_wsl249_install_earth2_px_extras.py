"""SSH 249: install Earth2Studio px optional deps (FCN uses PhysicsNeMo; SFNO uses Makani per pyproject)."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

KEY = Path.home() / ".ssh" / "id_ed25519"

# See earth2studio pyproject.toml optional-dependencies: fcn, sfno; uv.sources makani git rev.
SCRIPT = b"""#!/usr/bin/env bash
set -euo pipefail
PYS="${MYCOSOFT_EARTH2_PYTHON:-/root/mycosoft-venvs/mycosoft-earth2-wsl/bin/python}"
PIP="$(dirname "$PYS")/pip"
test -x "$PYS" || { echo "missing venv python: $PYS"; exit 1; }
"$PIP" install -U pip wheel setuptools
"$PIP" install --prefer-binary 'numpy>=1.26' 'cftime>=1.6.4'
# FCN (FourCastNet / AFNO)
"$PIP" install --prefer-binary 'nvidia-physicsnemo>=1.0.1'
# SFNO: Makani from NVIDIA/makani (same rev as earth2studio lockfile)
"$PIP" install --prefer-binary 'makani @ git+https://github.com/NVIDIA/makani.git@b38fcb2799d7dbc146fa60459f3f9823394a8bf1'
# Remaining SFNO extras (torch-harmonics etc.); best-effort.
"$PIP" install --prefer-binary 'pynvml>=12.0.0' 'ruamel.yaml>=0.18.10' 'scipy>=1.10.0' 'torch-harmonics>=0.8.0' || true
"$PIP" show nvidia-physicsnemo makani earth2studio 2>/dev/null | head -80
echo OK
"""

WIN_PATH = r"C:/Users/owner2/install-earth2-px-extras-wsl.sh"


def main() -> None:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.249", username="owner2", key_filename=str(KEY), timeout=30)

    sftp = c.open_sftp()
    with sftp.file(WIN_PATH, "wb") as f:
        f.write(SCRIPT.replace(b"\r\n", b"\n"))
    sftp.close()

    wsl = "wsl.exe -d Ubuntu -u root -- /bin/bash /mnt/c/Users/owner2/install-earth2-px-extras-wsl.sh"
    _, o, e = c.exec_command(wsl, timeout=2400)
    out = (o.read() + e.read()).decode("utf-8", errors="replace")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(out[-40000:])
    print("exit_status", o.channel.recv_exit_status(), flush=True)

    c.close()


if __name__ == "__main__":
    main()
