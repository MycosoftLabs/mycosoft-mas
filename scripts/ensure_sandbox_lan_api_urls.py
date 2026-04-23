#!/usr/bin/env python3
r"""
Set canonical LAN URLs for MINDEX + MAS in Sandbox website env files on 192.168.0.187
and recreate website blue/green containers from the website compose stack
(/opt/mycosoft/website: docker-compose.production.yml + docker-compose.production.blue-green.yml).

Merges .env in Python (reliable; avoids empty MINDEX_API_URL= lines from bad sed).
Loads password from MAS/website .credentials.local — never prints secrets.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import paramiko

MINDEX = "http://192.168.0.189:8000"
MAS = "http://192.168.0.188:8001"
REMOTE_ENVS = ("/opt/mycosoft/website/.env", "/opt/mycosoft/.env")
VM = "192.168.0.187"
WEBSITE_DIR = "/opt/mycosoft/website"
COMPOSE_FILES = "-f docker-compose.production.yml -f docker-compose.production.blue-green.yml"

EARTH2 = "http://192.168.0.249:8220"
VOICE = "192.168.0.241"
EARTH2_HOST = "192.168.0.249"

LAN_ENV_UPDATES: dict[str, str] = {
    "MINDEX_API_URL": MINDEX,
    "MINDEX_API_BASE_URL": MINDEX,
    "MAS_API_URL": MAS,
    "MAS_URL": MAS,
    "NEXT_PUBLIC_MAS_API_URL": MAS,
    # Split Legions (canonical: 241 voice, 249 earth2) — website + browser bundles
    "GPU_VOICE_IP": VOICE,
    "GPU_EARTH2_IP": EARTH2_HOST,
    "EARTH2_API_URL": EARTH2,
    "NEXT_PUBLIC_PERSONAPLEX_BRIDGE_URL": f"http://{VOICE}:8999",
    "NEXT_PUBLIC_PERSONAPLEX_BRIDGE_WS_URL": f"ws://{VOICE}:8999",
    "NEXT_PUBLIC_PERSONAPLEX_WS_URL": f"ws://{VOICE}:8999/api/chat",
    "NEXT_PUBLIC_CREP_BRIDGE_WS": f"ws://{VOICE}:8999/ws/crep/commands",
    "CREP_BRIDGE_WS": f"ws://{VOICE}:8999/ws/crep/commands",
}


def merge_env_file(content: str, updates: dict[str, str]) -> str:
    drop = set(updates.keys())
    lines_out: list[str] = []
    for line in content.splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            key = s.split("=", 1)[0].strip()
            if key in drop:
                continue
        lines_out.append(line)
    for k, v in updates.items():
        lines_out.append(f"{k}={v}")
    body = "\n".join(lines_out)
    if body and not body.endswith("\n"):
        body += "\n"
    return body


def load_creds() -> str:
    root = Path(__file__).resolve().parent.parent
    for p in (root / ".credentials.local", root.parent.parent / "WEBSITE" / "website" / ".credentials.local"):
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))
    pw = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD") or ""
    if not pw:
        raise SystemExit("Missing VM_PASSWORD in .credentials.local")
    return pw


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 600) -> tuple[int, str, str]:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return stdout.channel.recv_exit_status(), out, err


def main() -> int:
    if hasattr(__import__("sys").stdout, "reconfigure"):
        __import__("sys").stdout.reconfigure(encoding="utf-8", errors="replace")
    _pw = load_creds()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM, username="mycosoft", password=_pw, timeout=30)

    try:
        sftp = ssh.open_sftp()
        for remote in REMOTE_ENVS:
            try:
                with sftp.open(remote, "r") as rf:
                    raw = rf.read().decode("utf-8", errors="replace")
            except FileNotFoundError:
                print(f"Skip (missing): {remote}")
                continue
            run(ssh, f'cp -a "{remote}" "{remote}.bak.$(date +%Y%m%d_%H%M%S)"', timeout=60)
            new_body = merge_env_file(raw, LAN_ENV_UPDATES)
            with sftp.open(remote, "w") as wf:
                wf.write(new_body.encode("utf-8"))
            print(f"Updated {remote} ({len(new_body)} bytes); LAN API keys merged.")
        sftp.close()

        up = (
            f"cd {WEBSITE_DIR} && docker compose {COMPOSE_FILES} up -d --no-deps --force-recreate website-green website-blue"
        )
        print("Recreating website (blue/green) from website compose files …")
        code, o, e = run(ssh, up, timeout=900)
        print(o[-5000:] if len(o) > 5000 else o)
        if e.strip():
            print("stderr:", e[:2000])
        if code != 0:
            print("compose exit", code)
            return int(code)

        time.sleep(5)
        for label, u in [("mindex", f"{MINDEX}/health"), ("mas", f"{MAS}/health")]:
            _, o2, _ = run(ssh, f"curl -sS -o /dev/null -w '%{{http_code}}' --connect-timeout 5 {u}", timeout=25)
            print(f"from_sandbox_curl {label} -> HTTP {o2.strip()}")
        for c in ("mycosoft-website-green", "mycosoft-website-blue"):
            _, ev, _ = run(
                ssh,
                f"docker exec {c} printenv MINDEX_API_URL MAS_API_URL EARTH2_API_URL "
                f"GPU_VOICE_IP GPU_EARTH2_IP NEXT_PUBLIC_CREP_BRIDGE_WS 2>/dev/null || true",
                timeout=25,
            )
            if (ev or "").strip():
                print(f"{c} env:", (ev or "").strip()[:800])
        _, o3, _ = run(
            ssh,
            r'curl -sS -H "Accept: application/json" --connect-timeout 8 '
            r"http://127.0.0.1:3000/api/worldview/v1/health 2>/dev/null | head -c 1200",
            timeout=35,
        )
        snip = o3.replace("\n", " ")[:1200]
        print("worldview_v1_health_snippet:", snip)
        _, o4, _ = run(
            ssh,
            r'curl -sS --connect-timeout 12 "http://127.0.0.1:3000/api/worldview/snapshot" '
            r"2>/dev/null | head -c 4000",
            timeout=40,
        )
        sn4 = (o4 or "").replace("\n", " ")[:2000]
        print("worldview_snapshot_snippet:", sn4)
        if "earth2_api" in sn4 and "personaplex_voice" in sn4:
            print("worldview/snapshot: middleware keys present (JSON shape OK).")
        if snip.strip().startswith("<!DOCTYPE") or "<html" in snip[:200]:
            print(
                "Note: /api/worldview/v1/health returned HTML (middleware/auth or route on this build). "
                "Container printenv MINDEX/MAS above is the source of truth for this fix."
            )
    finally:
        ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
