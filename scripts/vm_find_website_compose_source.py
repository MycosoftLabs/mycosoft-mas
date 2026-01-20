#!/usr/bin/env python3
"""Find which docker compose config file(s) created the mycosoft website container on the VM."""

import paramiko
import sys

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"


def run(ssh: paramiko.SSHClient, cmd: str) -> str:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    return (out + ("\n" + err if err.strip() else "")).strip()


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)

    # Identify the website container
    container = run(ssh, "docker ps --format \"{{.Names}}\" | grep -E \"mycosoft-website|website\" | head -n 1 || true").strip()
    if not container:
        print("[ERROR] No website container found.")
        return
    print("[OK] Website container:", container)

    # Dump compose labels that reveal project + config files
    labels = run(
        ssh,
        f"docker inspect {container} --format '{{{{json .Config.Labels}}}}' | head -c 200000",
    )
    print("\n[labels]")
    print(labels)

    print("\n[compose metadata]")
    for key in (
        "com.docker.compose.project",
        "com.docker.compose.project.working_dir",
        "com.docker.compose.project.config_files",
        "com.docker.compose.service",
    ):
        print(f"- {key}: {run(ssh, f'docker inspect {container} --format \"{{{{ index .Config.Labels \\\"{key}\\\" }}}}\" || true')}")

    ssh.close()


if __name__ == "__main__":
    main()

