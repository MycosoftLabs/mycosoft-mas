#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx
import paramiko


def load_credentials() -> tuple[str, str]:
    root = Path(__file__).resolve().parent.parent
    candidates = [
        root / ".credentials.local",
        Path.home() / ".mycosoft-credentials",
    ]
    values: dict[str, str] = {}
    for path in candidates:
        if path.exists():
            for raw in path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
            break

    user = values.get("VM_SSH_USER", "mycosoft")
    password = values.get("VM_PASSWORD") or values.get("VM_SSH_PASSWORD") or ""
    if not password:
        raise RuntimeError("VM password not found in credential files.")
    return user, password


def health(url: str, timeout: float = 6.0) -> tuple[bool, str]:
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url)
            resp.raise_for_status()
            try:
                payload = resp.json()
            except Exception:
                payload = {"raw": resp.text}
            return True, json.dumps(payload, separators=(",", ":"))
    except Exception as exc:
        return False, str(exc)


def remote_sudo(ssh: paramiko.SSHClient, command: str, password: str) -> tuple[int, str, str]:
    stdin, stdout, stderr = ssh.exec_command(command, get_pty=False)
    if "sudo" in command:
        stdin.write(password + "\n")
        stdin.flush()
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    if password:
        out = out.replace(password, "***")
        err = err.replace(password, "***")
    return exit_code, out, err


def safe_print(text: str) -> None:
    print(text.encode("ascii", errors="replace").decode("ascii"))


def load_parser() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fix/diagnose sandbox MycoBrain service")
    parser.add_argument("--diagnose-only", action="store_true")
    parser.add_argument("--force-restart", action="store_true")
    return parser.parse_args()


def run_diag(ssh: paramiko.SSHClient, password: str) -> None:
    diag_cmds = [
        "systemctl is-active mycobrain-service || true",
        "systemctl status mycobrain-service --no-pager -l | tail -n 60 || true",
        "systemctl status mycobrain-proxy --no-pager -l | tail -n 60 || true",
        "ss -ltnp | grep 8003 || true",
        "ls -la /dev/serial/by-id 2>/dev/null || true",
        "ls -la /dev/ttyUSB* /dev/ttyACM* /dev/ttyTHS* 2>/dev/null || true",
        "journalctl -u mycobrain-service -n 80 --no-pager || true",
    ]
    for cmd in diag_cmds:
        code, out, err = remote_sudo(ssh, cmd, password)
        print(f"\nDIAG CMD: {cmd}\nEXIT: {code}")
        if out.strip():
            safe_print(out.strip())
        if err.strip():
            safe_print(err.strip())


def main() -> None:
    args = load_parser()

    local_ok, local_msg = health("http://localhost:8003/health")
    print(f"LOCAL {'OK' if local_ok else 'DOWN'} {local_msg}")

    sandbox_ok, sandbox_msg = health("http://192.168.0.187:8003/health")
    print(f"SANDBOX {'OK' if sandbox_ok else 'DOWN'} {sandbox_msg}")
    if sandbox_ok and not args.force_restart and not args.diagnose_only:
        return

    user, password = load_credentials()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect("192.168.0.187", username=user, password=password, timeout=20)

    if args.diagnose_only:
        run_diag(ssh, password)
    else:
        cmds = [
            "sudo -S systemctl restart mycobrain-service",
            "sudo -S systemctl restart mycobrain",
            "systemctl is-active mycobrain-service || true",
            "systemctl is-active mycobrain || true",
            "curl -fsS --max-time 8 http://localhost:8003/health || true",
        ]
        for cmd in cmds:
            code, out, err = remote_sudo(ssh, cmd, password)
            print(f"REMOTE CMD: {cmd}")
            print(f"EXIT: {code}")
            if out.strip():
                safe_print(out.strip())
            if err.strip():
                safe_print(err.strip())

    ssh.close()

    if args.diagnose_only:
        return

    sandbox_ok, sandbox_msg = health("http://192.168.0.187:8003/health")
    print(f"SANDBOX_AFTER {'OK' if sandbox_ok else 'DOWN'} {sandbox_msg}")
    if not sandbox_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
