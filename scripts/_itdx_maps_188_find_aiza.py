"""Find AIza assignments on 188 without printing values."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parents[1]
CREDS = ROOT / ".credentials.local"


def load_creds() -> None:
    for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def connect() -> paramiko.SSHClient:
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    pkey = paramiko.Ed25519Key.from_private_key_file(
        str(Path.home() / ".ssh" / "mycosoft_vm_automation_ed25519")
    )
    client.connect(
        "192.168.0.188",
        username="mycosoft",
        pkey=pkey,
        password=password,
        timeout=25,
        allow_agent=False,
        look_for_keys=False,
    )
    return client


def run_sudo(client: paramiko.SSHClient, cmd: str, timeout: int = 60) -> str:
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    stdin, stdout, stderr = client.exec_command(f"sudo -S -p '' {cmd}", timeout=timeout, get_pty=True)
    stdin.write(password + "\n")
    stdin.flush()
    stdin.channel.shutdown_write()
    out = stdout.read().decode("utf-8", "replace")
    if password:
        out = out.replace(password, "***")
    return out


def main() -> None:
    load_creds()
    client = connect()
    try:
        find_cmd = (
            "bash -lc "
            + repr(
                "echo FIND; "
                "find /home/mycosoft/mycosoft/mas /etc/mycosoft /etc/systemd/system/mas-orchestrator.service.d "
                "-type f \\( -name '.env*' -o -name '*credential*' -o -name '*maps*' -o -name '*google*' -o -name '*fusarium*' \\) "
                "2>/dev/null | head -80; "
                "echo GREP_FILES; "
                "grep -l 'AIza' /home/mycosoft/mycosoft/mas/.env /home/mycosoft/mycosoft/mas/.credentials.maps.env "
                "/etc/mycosoft/mas-compliance.env 2>/dev/null; "
                "echo UNIT_ENV_NAMES; "
                "tr '\\0' '\\n' < /proc/$(systemctl show -p MainPID --value mas-orchestrator)/environ 2>/dev/null "
                "| awk -F= '/GOOGLE|FUSARIUM|MAPS|GEMINI/ {print $1}'"
            )
        )
        print(run_sudo(client, find_cmd))
        dest = Path(tempfile.gettempdir()) / "itdx_188_compliance.env"
        print(run_sudo(client, "test -f /etc/mycosoft/mas-compliance.env && install -m 644 /etc/mycosoft/mas-compliance.env /tmp/itdx_comp.env && echo COMP_OK || echo COMP_ABSENT"))
        sftp = client.open_sftp()
        try:
            try:
                sftp.get("/tmp/itdx_comp.env", str(dest))
            except OSError as exc:
                print("SFTP_COMP", type(exc).__name__)
                dest = None
        finally:
            sftp.close()
        print(run_sudo(client, "rm -f /tmp/itdx_comp.env"))
        if dest and dest.exists():
            print("COMPLIANCE_BYTES", dest.stat().st_size)
            for line in dest.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line or line.lstrip().startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                name = name.strip()
                value = value.strip().strip('"').strip("'")
                if value.startswith("AIza"):
                    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
                    print(f"  {name} len={len(value)} sha256_12={digest}")
                elif any(n in name.upper() for n in ("GOOGLE", "FUSARIUM", "MAPS", "GEMINI")):
                    print(f"  {name} set={bool(value)} len={len(value)}")
            dest.unlink(missing_ok=True)
    finally:
        client.close()


if __name__ == "__main__":
    main()
