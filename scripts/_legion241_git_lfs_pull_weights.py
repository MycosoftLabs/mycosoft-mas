"""SSH 241: git lfs pull tokenizer safetensors inside real repo (shallow clone has .git)."""
from __future__ import annotations

from pathlib import Path

import paramiko

KEY = Path.home() / ".ssh" / "id_ed25519"
REPO = r"C:\Users\owner1\mycosoft-mas"


def main() -> None:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.241", username="owner1", key_filename=str(KEY), timeout=30)

    ps = (
        f"Set-Location '{REPO}'; git rev-parse --is-inside-work-tree; "
        "git lfs install; "
        "git lfs pull --include='models/personaplex-7b-v1/tokenizer-e351c8d8-checkpoint125.safetensors'"
    )
    _, o, e = c.exec_command(
        "powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command " + repr(ps),
        timeout=2400,
    )
    print((o.read() + e.read()).decode("utf-8", errors="replace")[-12000:])

    _, o2, e2 = c.exec_command(
        f'cmd.exe /c dir /-C "{REPO}\\models\\personaplex-7b-v1\\tokenizer-e351c8d8-checkpoint125.safetensors"',
        timeout=30,
    )
    print("=== tokenizer size after ===")
    print((o2.read() + e2.read()).decode("utf-8", "replace"))

    c.close()


if __name__ == "__main__":
    main()
