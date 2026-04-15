"""SSH to Earth-2 Legion 249 (owner2): add inbound TCP 8220 firewall rule; verify netsh."""
from __future__ import annotations

import sys
from pathlib import Path

import paramiko

HOST = "192.168.0.249"
USER = "owner2"
KEY = Path.home() / ".ssh" / "id_ed25519"
RULE = "Mycosoft-Earth2-TCP8220"


def main() -> None:
    if not KEY.is_file():
        print("Missing", KEY, file=sys.stderr)
        raise SystemExit(2)
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, key_filename=str(KEY), timeout=25, allow_agent=True, look_for_keys=True)

    # cmd.exe: no fragile quoting for rule name (no spaces)
    add = (
        f'cmd.exe /c netsh advfirewall firewall add rule name={RULE} '
        "dir=in action=allow protocol=TCP localport=8220 profile=private,domain"
    )
    show = f"cmd.exe /c netsh advfirewall firewall show rule name={RULE}"

    for label, cmd in [("add", add), ("show", show)]:
        print("===", label, "===")
        _, out, err = c.exec_command(cmd, timeout=60)
        o = out.read().decode("utf-8", errors="replace")
        e = err.read().decode("utf-8", errors="replace")
        print((o + e).strip() or "(empty)")

    c.close()
    print("OK")


if __name__ == "__main__":
    main()
