#!/usr/bin/env python3
import os
import time
from pathlib import Path

import paramiko


def load_credentials() -> None:
    creds_path = Path(__file__).resolve().parent.parent / ".credentials.local"
    if not creds_path.exists():
        return
    for line in creds_path.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()


def run_command(client: paramiko.SSHClient, password: str, command: str, timeout: int = 120) -> str:
    stdin, stdout, stderr = client.exec_command(f"sudo -S -p '' {command}", timeout=timeout)
    stdin.write(password + "\n")
    stdin.flush()
    out = stdout.read().decode(errors="replace").strip()
    err = stderr.read().decode(errors="replace").strip()
    return out or err


def main() -> None:
    load_credentials()
    user = os.environ.get("VM_SSH_USER", "mycosoft")
    password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
    if not password:
        raise RuntimeError("VM_PASSWORD not found.")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("192.168.0.189", username=user, password=password, timeout=30)

    print(run_command(client, password, "systemctl enable --now docker"))
    print(run_command(client, password, "systemctl restart docker"))
    print(run_command(client, password, "docker ps --format '{{.Names}} {{.Status}}'"))

    health_code = ""
    for _ in range(6):
        health_code = run_command(
            client,
            password,
        "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/mindex/health",
        )
        print(health_code)
        if health_code == "200":
            break
        time.sleep(10)

    if health_code != "200":
        print(run_command(client, password, "docker inspect --format '{{json .State.Health}}' mindex-api"))
        print(run_command(client, password, "docker logs --tail 200 mindex-api"))

    client.close()


if __name__ == "__main__":
    main()
