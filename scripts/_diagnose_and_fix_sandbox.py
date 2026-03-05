#!/usr/bin/env python3
"""
Diagnose sandbox VM 187 and optionally start container from existing image.
Run from website repo or MAS repo (loads creds from either).
"""
import os
import sys
from pathlib import Path

import paramiko

def load_credentials():
    for base in [
        Path(__file__).resolve().parent.parent,  # MAS repo
        Path(__file__).resolve().parent.parent.parent / "WEBSITE" / "website",
    ]:
        cf = base / ".credentials.local"
        if cf.exists():
            for line in cf.read_text().splitlines():
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()
            return

load_credentials()
host = "192.168.0.187"
user = os.environ.get("VM_SSH_USER", "mycosoft")
password = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
if not password:
    print("ERROR: VM_PASSWORD not set. Add .credentials.local")
    sys.exit(1)

def run(ssh, cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password, timeout=30)

    print("=== Docker images (website) ===")
    out, _ = run(ssh, "docker images mycosoft-always-on-mycosoft-website --format '{{.Repository}}:{{.Tag}} {{.CreatedSince}}'")
    print(out or "(none)")

    print("\n=== Running containers ===")
    out, _ = run(ssh, "docker ps -a --filter name=mycosoft-website --format '{{.Names}} {{.Status}}'")
    print(out or "(none)")

    print("\n=== Start container from existing image ===")
    run(ssh, "docker rm -f mycosoft-website 2>/dev/null || true")
    out, err = run(ssh, 
        "docker run -d --name mycosoft-website -p 3000:3000 "
        "-e NEXTAUTH_URL=https://sandbox.mycosoft.com "
        "-e AUTH_TRUST_HOST=true "
        "-v /opt/mycosoft/media/website/assets:/app/public/assets:ro "
        "--restart unless-stopped mycosoft-always-on-mycosoft-website:latest",
        timeout=30
    )
    if err and "Error" in err:
        print("Error:", err)
    else:
        print("Started:", out or "OK")

    print("\n=== Wait 15s and check health ===")
    import time
    time.sleep(15)
    out, _ = run(ssh, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
    print("HTTP:", out or "failed")

    ssh.close()
    print("\nDone. Purge Cloudflare cache if site is up.")

if __name__ == "__main__":
    main()
