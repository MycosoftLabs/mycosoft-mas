#!/usr/bin/env python3
"""Sync MINDEX_INTERNAL_TOKEN on Sandbox 187 website containers from local creds."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import paramiko

for creds_path in (
    Path(__file__).resolve().parents[3] / "WEBSITE" / "website" / ".env.local",
    Path(__file__).resolve().parents[3] / "WEBSITE" / "website" / ".credentials.local",
    Path(__file__).resolve().parents[1] / ".credentials.local",
):
    if creds_path.exists():
        for line in creds_path.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))

PASSWORD = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD", "")
TOKEN = (
    os.environ.get("MINDEX_INTERNAL_TOKEN")
    or (os.environ.get("MINDEX_INTERNAL_TOKENS") or "").split(",")[0]
    or os.environ.get("INTERNAL_API_SECRET")
    or ""
).strip()


def recreate_with_token(ssh: paramiko.SSHClient, name: str, token: str) -> bool:
    def run(cmd: str) -> tuple[int, str, str]:
        _, stdout, stderr = ssh.exec_command(cmd, timeout=180)
        return stdout.channel.recv_exit_status(), stdout.read().decode(), stderr.read().decode()

    code, out, _ = run(f"docker inspect {name} --format '{{{{json .}}}}' 2>/dev/null")
    if code != 0:
        print(f"{name}: NOT FOUND")
        return False

    info = json.loads(out)
    image = info["Config"]["Image"]
    ports = info.get("HostConfig", {}).get("PortBindings") or {}
    mounts = info.get("Mounts") or []
    envs = [e for e in (info["Config"].get("Env") or []) if not e.startswith("MINDEX_INTERNAL_TOKEN=")]
    envs.append(f"MINDEX_INTERNAL_TOKEN={token}")

    port_args = ""
    for container_port, bindings in ports.items():
        if bindings:
            host_port = bindings[0].get("HostPort")
            if host_port:
                port_args += f" -p {host_port}:{container_port.split('/')[0]}"

    vol_args = ""
    for m in mounts:
        if m.get("Type") == "bind" and m.get("Source") and m.get("Destination"):
            ro = ":ro" if not m.get("RW", True) else ""
            vol_args += f" -v {m['Source']}:{m['Destination']}{ro}"

    env_shell = " ".join(f"-e {json.dumps(e)}" for e in envs)
    restart = info.get("HostConfig", {}).get("RestartPolicy", {}).get("Name", "unless-stopped")
    run_cmd = (
        f"docker stop {name} && docker rm {name} && "
        f"docker run -d --name {name}{port_args}{vol_args} {env_shell} "
        f"--restart {restart} {image}"
    )
    code, out, err = run(run_cmd)
    ok = code == 0
    print(f"{name}: recreate={'ok' if ok else 'fail'} token={'SET' if token else 'UNSET'}")
    if not ok and err.strip():
        print(f"{name}_err={err.strip()[:160]}")
    return ok


def main() -> int:
    if not PASSWORD:
        print("ERROR: VM_PASSWORD not loaded")
        return 1
    if not TOKEN:
        print("ERROR: MINDEX_INTERNAL_TOKEN not found in local env/credentials")
        return 1

    print(f"local_token={'SET' if TOKEN else 'UNSET'}")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    for user in ("mycosoft", os.environ.get("VM_SSH_USER", "")):
        if not user:
            continue
        try:
            ssh.connect("192.168.0.187", username=user, password=PASSWORD, timeout=30)
            print(f"ssh_user={user}")
            break
        except Exception:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    else:
        print("ERROR: SSH failed")
        return 1

    ok_any = False
    for name in ("mycosoft-website", "mycosoft-website-blue", "mycosoft-website-green"):
        if recreate_with_token(ssh, name, TOKEN):
            ok_any = True

    ssh.close()
    return 0 if ok_any else 1


if __name__ == "__main__":
    sys.exit(main())
