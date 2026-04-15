"""SSH 241: pip install einops (and sync voice requirements) into .personaplex-venv."""
from __future__ import annotations

from pathlib import Path

import paramiko

KEY = Path.home() / ".ssh" / "id_ed25519"
PIP = r"C:\Users\owner1\.personaplex-venv\Scripts\pip.exe"


def main() -> None:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.241", username="owner1", key_filename=str(KEY), timeout=30)
    # Avoid nested quotes in cmd.exe — invoke pip.exe directly.
    cmd = f"{PIP} install -q einops sphn sentencepiece"
    _, o, e = c.exec_command(cmd, timeout=300)
    print((o.read() + e.read()).decode("utf-8", "replace")[-4000:])
    c.close()


if __name__ == "__main__":
    main()
