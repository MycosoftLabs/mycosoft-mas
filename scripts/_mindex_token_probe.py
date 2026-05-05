"""One-shot: list env key names on MINDEX VM (no values)."""
import os
import sys
from pathlib import Path


def load_creds() -> None:
    for p in [
        Path(__file__).resolve().parent.parent / ".credentials.local",
        Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.credentials.local"),
    ]:
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main() -> int:
    load_creds()
    import paramiko

    pw = (os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or "").strip()
    if not pw:
        print("no_password")
        return 1
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.189", username="mycosoft", password=pw, timeout=15, allow_agent=False, look_for_keys=False)
    cmds = [
        "ss -lntp | grep -E ':8000|:6379' || true",
        "docker ps --format '{{.Names}}' 2>/dev/null | head -10",
        "for f in /opt/mindex/.env /home/mycosoft/mindex/.env; do test -f $f && echo FILE:$f && grep -E '^MINDEX_INTERNAL|^INTERNAL' $f 2>/dev/null | sed 's/=.*/=***REDACTED***/'; done",
    ]
    for cmd in cmds:
        print("---", cmd[:50], "---")
        _, out, err = c.exec_command(cmd, timeout=45)
        sys.stdout.write(out.read().decode(errors="replace"))
        sys.stdout.write(err.read().decode(errors="replace"))
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
