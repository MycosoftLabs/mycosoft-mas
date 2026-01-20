#!/usr/bin/env python3
"""Patch the sandbox VM docker-compose.always-on.yml to point website -> Windows MycoBrain service.

On sandbox today, the website container is configured with:
  MYCOBRAIN_SERVICE_URL=http://mycobrain:8003
but there is no `mycobrain` container in the always-on stack, so /api/mycobrain calls hang and Cloudflare returns 504.
This script updates the compose file used by the running website service:
  /home/mycosoft/mycosoft/mas/docker-compose.always-on.yml
to:
  MYCOBRAIN_SERVICE_URL=http://192.168.0.172:18003
and then force-recreates only the website container.
"""

from __future__ import annotations

import datetime as dt
from io import StringIO

import paramiko
import yaml

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"

COMPOSE_PATH = "/home/mycosoft/mycosoft/mas/docker-compose.always-on.yml"

TARGET_URL = "http://192.168.0.172:18003"


def run(ssh: paramiko.SSHClient, cmd: str) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return (out + ("\n" + err if err.strip() else "")).strip()


def main() -> None:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)

    raw = run(ssh, f"cat {COMPOSE_PATH}")
    doc = yaml.safe_load(StringIO(raw)) or {}

    services = doc.get("services") or {}
    website = services.get("mycosoft-website")
    if not isinstance(website, dict):
        raise SystemExit("[ERROR] services.mycosoft-website not found in compose file")

    env = website.get("environment")
    if env is None:
        env = {}
        website["environment"] = env

    if isinstance(env, list):
        # Convert list-style env to map for deterministic patching
        env_map = {}
        for item in env:
            if isinstance(item, str) and "=" in item:
                k, v = item.split("=", 1)
                env_map[k] = v
        env = env_map
        website["environment"] = env

    if not isinstance(env, dict):
        raise SystemExit("[ERROR] Unsupported environment format for mycosoft-website")

    prev = env.get("MYCOBRAIN_SERVICE_URL")
    env["MYCOBRAIN_SERVICE_URL"] = TARGET_URL

    # Write back
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = f"{COMPOSE_PATH}.bak-{ts}"
    run(ssh, f"cp {COMPOSE_PATH} {backup}")

    new_raw = yaml.dump(doc, sort_keys=False)
    run(ssh, "cat > /tmp/docker-compose.always-on.yml << 'EOF'\n" + new_raw + "\nEOF")
    run(ssh, f"mv /tmp/docker-compose.always-on.yml {COMPOSE_PATH}")

    print("[OK] Updated compose:", COMPOSE_PATH)
    print(" - previous MYCOBRAIN_SERVICE_URL:", prev)
    print(" - new MYCOBRAIN_SERVICE_URL:", TARGET_URL)
    print(" - backup:", backup)

    # Recreate only website container
    print("\n[recreate] docker compose up -d --no-deps --force-recreate mycosoft-website")
    print(
        run(
            ssh,
            f"cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml up -d --no-deps --force-recreate mycosoft-website",
        )
    )

    # Verify env inside container
    print("\n[verify env]")
    print(
        run(
            ssh,
            "cid=$(docker ps --format \"{{.Names}}\" | grep -E \"mycosoft-website|website\" | head -n 1); "
            "docker inspect \"$cid\" --format \"{{range .Config.Env}}{{println .}}{{end}}\" | grep -E \"MYCOBRAIN_SERVICE_URL\" || true",
        )
    )

    ssh.close()


if __name__ == "__main__":
    main()

