"""SSH+SFTP 241: upload Legion .lfsconfig without fetchexclude, then git lfs pull tokenizer."""
from __future__ import annotations

from pathlib import Path

import paramiko

KEY = Path.home() / ".ssh" / "id_ed25519"
REMOTE = r"C:\Users\owner1\mycosoft-mas\.lfsconfig"
LFS_BODY = (
    "# Voice Legion - LFS fetch allowed for PersonaPlex weights (Apr 2026).\n"
    "[lfs]\n"
    "\tconcurrenttransfers = 1\n"
).encode("utf-8")


def main() -> None:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.241", username="owner1", key_filename=str(KEY), timeout=30)
    sftp = c.open_sftp()
    with sftp.file(REMOTE.replace("\\", "/"), "wb") as f:
        f.write(LFS_BODY)
    sftp.close()

    ps = (
        "Set-Location 'C:\\Users\\owner1\\mycosoft-mas'; "
        "Get-Content '.lfsconfig'; "
        "git lfs env | Select-String -Pattern 'FetchExclude|FetchInclude'; "
        "git lfs pull --include='models/personaplex-7b-v1/tokenizer-e351c8d8-checkpoint125.safetensors'; "
        "(Get-Item 'models\\personaplex-7b-v1\\tokenizer-e351c8d8-checkpoint125.safetensors').Length"
    )
    _, o, e = c.exec_command(
        "powershell -NoProfile -ExecutionPolicy Bypass -Command " + repr(ps),
        timeout=2400,
    )
    print((o.read() + e.read()).decode("utf-8", errors="replace"))
    c.close()


if __name__ == "__main__":
    main()
