#!/usr/bin/env python3
"""One-shot: check sandbox website container mounts and /app/public/assets."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import paramiko

REPO = Path(__file__).resolve().parent.parent
for f in (REPO / ".credentials.local", REPO.parent / "website" / ".credentials.local"):
    if f.exists():
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if line and not line.strip().startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))

pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
if not pw:
    print("no VM password")
    sys.exit(1)


def run(c: paramiko.SSHClient, cmd: str) -> str:
    _, out, err = c.exec_command(cmd, timeout=90)
    o = out.read().decode(errors="replace")
    e = err.read().decode(errors="replace")
    return o + (f"\n[stderr]\n{e}" if e.strip() else "")


def main() -> int:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect("192.168.0.187", username="mycosoft", password=pw, timeout=25)

    print("=== docker ps (website) ===")
    print(run(c, "docker ps -a --format '{{.Names}}\t{{.Status}}' | grep -i website || true"))

    # Production compose often uses website-website-1; legacy name was mycosoft-website
    name = (
        run(c, "docker ps --filter publish=3000 --format '{{.Names}}' 2>&1")
        .strip()
        .split("\n")[0]
        .strip()
    )
    if not name or "Error" in name:
        name = "mycosoft-website"
    inspect_test = run(c, f"docker inspect {name} --format '{{{{.Name}}}}' 2>&1").strip()
    if "no such object" in inspect_test.lower() or not inspect_test.startswith("/"):
        print("=== resolve container by image/name ===")
        name = (
            run(
                c,
                "docker ps --format '{{.Names}}' | grep -E 'website|mycosoft-website' | head -1",
            )
            .strip()
            .split("\n")[0]
            .strip()
        )
    if not name:
        print("no running website container found")
        print(run(c, "docker ps -a --format '{{.Names}}' | head -20"))
        c.close()
        return 1
    print(f"=== using container: {name} ===")

    print("=== mounts (json) ===")
    mounts_json = run(c, f"docker inspect {name} --format '{{{{json .Mounts}}}}' 2>&1").strip()
    try:
        mounts = json.loads(mounts_json)
        for m in mounts:
            print(
                f"  {m.get('Type')} {m.get('Source')} -> {m.get('Destination')} "
                f"ro={m.get('RW') is False}"
            )
    except Exception as ex:
        print("parse error:", ex)
        print(mounts_json[:1500])

    print(f"=== ls /app/public/assets in {name} ===")
    print(run(c, f"docker exec {name} ls -la /app/public/assets 2>&1 | head -25"))

    print("=== sample homepage + mushroom1 ===")
    print(
        run(
            c,
            f"docker exec {name} sh -c 'ls -la /app/public/assets/homepage 2>&1; echo ---; ls -la /app/public/assets/mushroom1 2>&1 | head -10'",
        )
    )

    print("=== wget inside container (localhost:3000) ===")
    print(
        run(
            c,
            f"docker exec {name} sh -c \"wget -q -S -O /dev/null 'http://127.0.0.1:3000/assets/homepage/Mycosoft%20Background.mp4' 2>&1 | head -20\"",
        )
    )

    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
