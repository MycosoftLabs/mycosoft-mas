#!/usr/bin/env python3
"""One-shot: SSH 187, GET /api/worldview/snapshot, print middleware keys (UTF-8 safe)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import paramiko

VM = "192.168.0.187"


def load_pw() -> str:
    root = Path(__file__).resolve().parent.parent
    for p in (root / ".credentials.local", root.parent.parent / "WEBSITE" / "website" / ".credentials.local"):
        if not p.is_file():
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    if not pw:
        raise SystemExit("Missing VM_PASSWORD")
    return pw


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pw = load_pw()
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(VM, username="mycosoft", password=pw, timeout=35)
    try:
        _, stdout, stderr = c.exec_command(
            "curl -sS -m 35 http://127.0.0.1:3000/api/worldview/snapshot",
            timeout=50,
        )
        raw = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        if err.strip():
            print("stderr:", err[:500], file=sys.stderr)
        try:
            d = json.loads(raw)
        except json.JSONDecodeError as e:
            print("not_json:", raw[:400])
            return 1
        m = d.get("middleware") or {}
        e2 = m.get("earth2_api")
        pp = m.get("personaplex_voice")
        print("earth2_api:", json.dumps(e2, ensure_ascii=False)[:500])
        print("personaplex_voice_url:", (pp or {}).get("url"))
        print("snapshot_latency_ms:", d.get("latency_ms"))
    finally:
        c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
