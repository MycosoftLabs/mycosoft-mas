#!/usr/bin/env python3
"""
Generate and optionally apply Jetson MQTT env in one command.

Modes:
- lan:    mqtt://192.168.0.196:1883 (fastest on local network)
- remote: wss://mqtt.mycosoft.com:443 (public over Cloudflare TLS)

Env inputs:
- MQTT_BROKER_PASSWORD (preferred) or VM_PASSWORD
- JETSON_IP (default 192.168.0.123)
- JETSON_SSH_USER (default jetson)
- JETSON_SSH_PASSWORD (required for --apply if keys unavailable)

Date: 2026-04-08
"""
from __future__ import annotations

import argparse
import base64
import os
import shlex
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from infra.csuite.paramiko_ssh_dual import ssh_client_password_or_keyboard_interactive  # noqa: E402


def _load_creds() -> None:
    for base in (REPO, Path.cwd()):
        for name in (".credentials.local", ".env.local", ".env"):
            p = base / name
            if not p.exists():
                continue
            for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
                if not raw or raw.startswith("#") or "=" not in raw:
                    continue
                key, _, val = raw.partition("=")
                key = key.strip()
                val = val.strip().strip("\"'")
                if key and key not in os.environ:
                    os.environ[key] = val


def _render_env(mode: str, mqtt_password: str) -> str:
    if mode == "remote":
        broker_url = "wss://mqtt.mycosoft.com:443"
        transport = "websockets"
    else:
        broker_url = "mqtt://192.168.0.196:1883"
        transport = "tcp"

    return (
        f"MYCOBRAIN_MQTT_URL={broker_url}\n"
        "MYCOBRAIN_MQTT_USERNAME=mycobrain\n"
        f"MYCOBRAIN_MQTT_PASSWORD={mqtt_password}\n"
        f"MYCOBRAIN_MQTT_TRANSPORT={transport}\n"
        "MYCOBRAIN_MQTT_WS_PATH=/\n"
    )


def _apply_remote(host: str, user: str, password: str, remote_path: str, content: str) -> None:
    client = ssh_client_password_or_keyboard_interactive(host, user, password, timeout=30.0)
    b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
    normalized = remote_path.replace("\\", "/")
    if normalized.startswith("~/"):
        shell_remote = "$HOME/" + normalized[2:]
    else:
        shell_remote = normalized
    parent = str(Path(shell_remote).parent).replace("\\", "/")
    cmd = (
        "set -euo pipefail; "
        f"install -d -m 700 {shlex.quote(parent)}; "
        f"echo {shlex.quote(b64)} | base64 -d > {shlex.quote(shell_remote)}; "
        f"chmod 600 {shlex.quote(shell_remote)}; "
        f"echo 'Wrote {shell_remote}'"
    )
    stdin, stdout, stderr = client.exec_command("bash -lc " + shlex.quote(cmd), get_pty=True)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    client.close()
    if out.strip():
        print(out.strip())
    if err.strip():
        print(err.strip(), file=sys.stderr)
    if code != 0:
        raise RuntimeError(f"Remote write failed with exit code {code}")


def main() -> int:
    _load_creds()

    parser = argparse.ArgumentParser(description="Bootstrap Jetson MQTT env.")
    parser.add_argument("--mode", choices=["lan", "remote"], default="lan")
    parser.add_argument("--output", default=str(REPO / "_jetson_mqtt.env"))
    parser.add_argument("--apply", action="store_true", help="Apply env file to Jetson over SSH")
    parser.add_argument("--jetson-host", default=(os.environ.get("JETSON_IP") or "192.168.0.123"))
    parser.add_argument("--jetson-user", default=(os.environ.get("JETSON_SSH_USER") or "jetson"))
    parser.add_argument("--remote-path", default="~/.mycosoft/mycobrain_mqtt.env")
    args = parser.parse_args()

    mqtt_password = (os.environ.get("MQTT_BROKER_PASSWORD") or os.environ.get("VM_PASSWORD") or "").strip()
    if not mqtt_password:
        print("ERROR: Set MQTT_BROKER_PASSWORD (preferred) or VM_PASSWORD.", file=sys.stderr)
        return 1

    content = _render_env(args.mode, mqtt_password)
    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    print(f"Wrote local env file: {out_path}")

    if args.apply:
        jetson_password = (os.environ.get("JETSON_SSH_PASSWORD") or os.environ.get("VM_PASSWORD") or "").strip()
        if not jetson_password:
            print("ERROR: --apply requires JETSON_SSH_PASSWORD (or VM_PASSWORD).", file=sys.stderr)
            return 1
        _apply_remote(
            host=args.jetson_host,
            user=args.jetson_user,
            password=jetson_password,
            remote_path=args.remote_path,
            content=content,
        )
        print(f"Applied env to {args.jetson_user}@{args.jetson_host}:{args.remote_path}")

    if args.apply:
        print("\nNext on Jetson:")
        print(f"  source {args.remote_path}")
        print("  # restart your publisher/service after sourcing env")
    else:
        print("\nNext:")
        print(f"  copy {out_path.name} to Jetson, then run:")
        print("  source ~/.mycosoft/mycobrain_mqtt.env")
        print("  # restart your publisher/service after sourcing env")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
