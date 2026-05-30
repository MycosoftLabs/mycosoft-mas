#!/usr/bin/env python3
"""SSH helper to run Hyphae Pi flash sidecar (Phase B)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import paramiko


def _load_credentials_file() -> None:
    creds = Path(__file__).resolve().parents[1] / ".credentials.local"
    if not creds.exists():
        return
    for line in creds.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def load_credential_attempts() -> list[tuple[str, str]]:
    """Return SSH (user, password) pairs in priority order for Hyphae Pi (228)."""
    _load_credentials_file()

    jetson_user = os.environ.get("JETSON_SSH_USER", "jetson").strip() or "jetson"
    jetson_pass = (
        os.environ.get("JETSON_SSH_PASSWORD", "").strip()
        or os.environ.get("VM_PASSWORD", "").strip()
        or os.environ.get("VM_SSH_PASSWORD", "").strip()
    )
    hyphae_user = os.environ.get("HYPHAE_SSH_USER", "").strip()
    hyphae_pass = (
        os.environ.get("HYPHAE_SSH_PASSWORD", "").strip()
        or jetson_pass
    )
    vm_pass = (
        os.environ.get("VM_PASSWORD", "").strip()
        or os.environ.get("VM_SSH_PASSWORD", "").strip()
    )

    if not jetson_pass and not hyphae_pass and not vm_pass:
        raise SystemExit(
            "No SSH password for Hyphae Pi probe. Set in MAS .credentials.local or env:\n"
            "  JETSON_SSH_USER=jetson\n"
            "  JETSON_SSH_PASSWORD=<same as Jetson 123 or VM_PASSWORD>\n"
            "Optional fallbacks: HYPHAE_SSH_USER, HYPHAE_SSH_PASSWORD, VM_PASSWORD"
        )

    attempts: list[tuple[str, str]] = []

    def add(user: str, password: str) -> None:
        if user and password and (user, password) not in attempts:
            attempts.append((user, password))

    add(jetson_user, jetson_pass or vm_pass)
    if hyphae_user:
        add(hyphae_user, hyphae_pass or vm_pass)
    add("pi", vm_pass)
    add("mycosoft", vm_pass)

    return attempts


def load_creds() -> tuple[str, str, list[str]]:
    attempts = load_credential_attempts()
    users = [user for user, _ in attempts]
    return users[0], attempts[0][1], users


def ssh_exec(host: str, command: str, timeout: int = 120) -> dict:
    attempts = load_credential_attempts()
    users = [user for user, _ in attempts]
    last_err: Exception | None = None
    for user, password in attempts:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(host, username=user, password=password, timeout=30)
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            out = stdout.read().decode("utf-8", errors="replace")
            err = stderr.read().decode("utf-8", errors="replace")
            code = stdout.channel.recv_exit_status()
            return {"exit_code": code, "stdout": out, "stderr": err, "ssh_user": user}
        except paramiko.AuthenticationException as exc:
            last_err = exc
        finally:
            client.close()
    raise SystemExit(f"SSH authentication failed for {host} (tried {users}): {last_err}")


def scp_file(host: str, local_path: Path, remote_path: str) -> None:
    attempts = load_credential_attempts()
    users = [user for user, _ in attempts]
    last_err: Exception | None = None
    for user, password in attempts:
        transport = paramiko.Transport((host, 22))
        try:
            transport.connect(username=user, password=password)
            sftp = paramiko.SFTPClient.from_transport(transport)
            try:
                sftp.put(str(local_path), remote_path)
                return
            finally:
                sftp.close()
        except paramiko.AuthenticationException as exc:
            last_err = exc
        finally:
            transport.close()
    raise SystemExit(f"SCP authentication failed for {host} (tried {users}): {last_err}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="192.168.0.228")
    parser.add_argument("--artifact", default="")
    parser.add_argument("--sidecar", default=str(Path(__file__).resolve().parents[1] / "services/mycobrain/pi_flash_sidecar.py"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--probe-only", action="store_true")
    args = parser.parse_args()

    if args.probe_only:
        cmds = [
            "uname -a",
            "ls -la /dev/ttyACM* 2>/dev/null || true",
            "curl -s -m 5 localhost:8787/api/status | head -c 400",
            "curl -s -m 3 localhost:18789/health || echo openclaw_unreachable",
        ]
        report = {}
        for c in cmds:
            report[c] = ssh_exec(args.host, c, timeout=30)
        print(json.dumps(report, indent=2))
        return 0

    if not args.artifact:
        raise SystemExit("--artifact is required unless --probe-only")

    artifact = Path(args.artifact)
    if not artifact.is_file():
        raise SystemExit(f"Missing artifact: {artifact}")

    remote_dir = "/tmp/mycobrain_flash"
    remote_artifact = f"{remote_dir}/{artifact.name}"
    remote_sidecar = f"{remote_dir}/pi_flash_sidecar.py"

    ssh_exec(args.host, f"mkdir -p {remote_dir}")
    scp_file(args.host, artifact, remote_artifact)
    scp_file(args.host, Path(args.sidecar), remote_sidecar)

    flags = "--dry-run" if args.dry_run else ""
    if args.confirm:
        flags += " --confirm"
    env_prefix = "APPROVE_FLASH=true " if args.confirm else ""
    cmd = f"{env_prefix}python3 {remote_sidecar} --port /dev/ttyACM0 --artifact {remote_artifact} {flags}"
    result = ssh_exec(args.host, cmd, timeout=600)
    # Emit sidecar JSON on stdout for MAS firmware_flash_api relay parsing
    sidecar_out = (result.get("stdout") or "").strip()
    if sidecar_out:
        print(sidecar_out)
    else:
        print(json.dumps(result, indent=2))
    return 0 if result.get("exit_code") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
