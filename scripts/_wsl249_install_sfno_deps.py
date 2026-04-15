"""SSH 249: SFTP bash to Windows, run in WSL as root — install Makani + earth2studio[sfno] in Earth-2 venv."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

KEY = Path.home() / ".ssh" / "id_ed25519"

SCRIPT = b"""#!/usr/bin/env bash
set -euo pipefail
PYS="${MYCOSOFT_EARTH2_PYTHON:-/root/mycosoft-venvs/mycosoft-earth2-wsl/bin/python}"
PIP="$(dirname "$PYS")/pip"
test -x "$PYS" || { echo "missing venv python: $PYS"; exit 1; }
"$PIP" --version
"$PIP" install -U pip wheel setuptools
# Pre-install numpy + binary cftime so pip does not backtrack into ancient sdist builds.
"$PIP" install --prefer-binary numpy 'cftime>=1.6.4'
# SFNO: Modulus Makani (required by earth2studio.models.px.SFNO)
"$PIP" install --prefer-binary 'makani[all] @ git+https://github.com/NVIDIA/modulus-makani.git@v0.1.0'
# Extra deps for SFNO model package
if "$PIP" show nvidia-earth2studio >/dev/null 2>&1; then
  "$PIP" install --prefer-binary 'nvidia-earth2studio[sfno]'
else
  "$PIP" install --prefer-binary 'earth2studio[sfno]'
fi
"$PIP" show earth2studio 2>/dev/null || "$PIP" show nvidia-earth2studio
echo OK
"""

WIN_PATH = r"C:/Users/owner2/install-sfno-deps-wsl.sh"


def main() -> None:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.249", username="owner2", key_filename=str(KEY), timeout=30)

    sftp = c.open_sftp()
    with sftp.file(WIN_PATH, "wb") as f:
        f.write(SCRIPT.replace(b"\r\n", b"\n"))
    sftp.close()

    wsl = "wsl.exe -d Ubuntu -u root -- /bin/bash /mnt/c/Users/owner2/install-sfno-deps-wsl.sh"
    _, o, e = c.exec_command(wsl, timeout=2400)
    out = (o.read() + e.read()).decode("utf-8", errors="replace")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(out[-32000:])
    print("exit_status", o.channel.recv_exit_status(), flush=True)

    c.close()


if __name__ == "__main__":
    main()
