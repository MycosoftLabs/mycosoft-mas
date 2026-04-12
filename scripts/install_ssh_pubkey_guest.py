#!/usr/bin/env python3
"""
Append local SSH public key to guest user authorized_keys (password / keyboard-interactive).

Does not use local private keys for auth (so a wrong key on disk does not block install).

Env:
  MQTT_VM_GUEST_IP / MQTT_VM_HOST  default 192.168.0.196
  MQTT_VM_SSH_USER                 default mycosoft
  VM_PASSWORD / VM_SSH_PASSWORD    required (never commit)
  SSH_PUBKEY_PATH                  optional; default ~/.ssh/id_ed25519.pub then id_rsa.pub

Date: 2026-04-08
"""
from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from infra.csuite.paramiko_ssh_dual import ssh_client_password_or_keyboard_interactive  # noqa: E402


def _find_pubkey() -> Path:
    custom = (os.environ.get("SSH_PUBKEY_PATH") or "").strip()
    if custom:
        p = Path(custom).expanduser()
        if p.is_file():
            return p
        print(f"ERROR: SSH_PUBKEY_PATH not a file: {p}", file=sys.stderr)
        sys.exit(1)
    home = Path.home() / ".ssh"
    for name in ("id_ed25519.pub", "id_rsa.pub", "id_ecdsa.pub"):
        p = home / name
        if p.is_file():
            return p
    print("ERROR: No id_ed25519.pub or id_rsa.pub in ~/.ssh (set SSH_PUBKEY_PATH)", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    host = (os.environ.get("MQTT_VM_GUEST_IP") or os.environ.get("MQTT_VM_HOST") or "192.168.0.196").strip()
    user = (os.environ.get("MQTT_VM_SSH_USER") or "mycosoft").strip()
    pw = (
        (os.environ.get("MQTT_VM_SSH_PASSWORD") or os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or "")
        .strip()
    )
    if not pw:
        print("ERROR: Set VM_PASSWORD (or VM_SSH_PASSWORD)", file=sys.stderr)
        return 1

    key_path = _find_pubkey()
    key_line = key_path.read_text(encoding="utf-8").strip()
    if not key_line or not key_line.startswith(("ssh-ed25519 ", "ssh-rsa ", "ecdsa-")):
        print(f"ERROR: Invalid or empty public key: {key_path}", file=sys.stderr)
        return 1

    key_b64 = base64.b64encode(key_line.encode("utf-8")).decode("ascii")

    try:
        client = ssh_client_password_or_keyboard_interactive(host, user, pw, timeout=30.0)
    except Exception as e:
        print(f"ERROR: SSH login failed: {e}", file=sys.stderr)
        return 1

    remote = f"""set -euo pipefail
install -d -m 700 "$HOME/.ssh"
f="$HOME/.ssh/authorized_keys"
KEYLINE=$(echo {key_b64} | base64 -d)
if grep -qxF "$KEYLINE" "$f" 2>/dev/null; then
  echo "Key already present in authorized_keys."
else
  echo "$KEYLINE" >> "$f"
  echo "Key appended to authorized_keys."
fi
chmod 600 "$f"
"""
    stdin, stdout, stderr = client.exec_command("bash -lc " + __import__("shlex").quote(remote), get_pty=True)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    client.close()

    sys.stdout.buffer.write((out + "\n").encode("utf-8", errors="replace"))
    if err.strip():
        sys.stderr.buffer.write(err.encode("utf-8", errors="replace"))
        sys.stderr.buffer.write(b"\n")
    return 0 if code == 0 else code


if __name__ == "__main__":
    raise SystemExit(main())
