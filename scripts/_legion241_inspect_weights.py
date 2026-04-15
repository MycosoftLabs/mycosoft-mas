"""SSH 241: list weight sizes; detect Git LFS pointer in tokenizer safetensors."""
from __future__ import annotations

from pathlib import Path

import paramiko

KEY = Path.home() / ".ssh" / "id_ed25519"
BASE = r"C:\Users\owner1\mycosoft-mas"


def main() -> None:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.241", username="owner1", key_filename=str(KEY), timeout=30)

    _, o, e = c.exec_command(
        f'cmd.exe /c dir /-C "{BASE}\\models\\personaplex-7b-v1\\*.safetensors"',
        timeout=45,
    )
    print("=== dir safetensors ===")
    print((o.read() + e.read()).decode("utf-8", "replace"))

    tok = f"{BASE}\\models\\personaplex-7b-v1\\tokenizer-e351c8d8-checkpoint125.safetensors"
    _, o2, e2 = c.exec_command(
        f'cmd.exe /c powershell -NoProfile -Command "[System.IO.File]::ReadAllText(\'{tok}\')[0..200] -join \'\'"',
        timeout=30,
    )
    print("=== tokenizer head (text) ===")
    print((o2.read() + e2.read()).decode("utf-8", errors="replace")[:500])

    c.close()


if __name__ == "__main__":
    main()
