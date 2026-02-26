#!/usr/bin/env python3
"""Check website container on Sandbox 187; if not running, rebuild and run. Verify curl, purge Cloudflare."""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CREDS = REPO / ".credentials.local"
if not CREDS.exists():
    print("ERROR: .credentials.local not found")
    sys.exit(1)
for line in CREDS.read_text().splitlines():
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

VM_PASS = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
if not VM_PASS:
    print("ERROR: VM_PASSWORD or VM_SSH_PASSWORD not set")
    sys.exit(1)

import paramiko

HOST = "192.168.0.187"
USER = "mycosoft"


def run(ssh, cmd, timeout=60):
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    return code, out, err


def main():
    print("Connecting to 192.168.0.187...")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, username=USER, password=VM_PASS, timeout=30)

    # 1. Check container status
    print("\n=== 1. docker ps (mycosoft-website) ===")
    code, out, err = run(c, "docker ps -a --filter name=mycosoft-website --format 'table {{.Names}}\t{{.Status}}'", 15)
    full = out + err
    print(full)
    running = "mycosoft-website" in full and "Up" in full

    if running:
        print("Container is RUNNING. Skipping rebuild.")
    else:
        print("Container NOT running. Pull, rebuild, run...")
        # Stop/remove if exists
        run(c, "docker stop mycosoft-website 2>/dev/null; docker rm mycosoft-website 2>/dev/null; echo done", 30)
        build_cmd = (
            "cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main && "
            "docker build --network host --no-cache -t mycosoft-always-on-mycosoft-website:latest ."
        )
        code, out, err = run(c, build_cmd, timeout=2700)
        if code != 0:
            print("BUILD FAILED")
            print((out + err)[-3000:])
            c.close()
            sys.exit(1)
        print("Build OK.")
        run_cmd = (
            "docker run -d --name mycosoft-website -p 3000:3000 "
            "-v /opt/mycosoft/media/website/assets:/app/public/assets:ro "
            "-e MAS_API_URL=http://192.168.0.188:8001 --restart unless-stopped "
            "mycosoft-always-on-mycosoft-website:latest"
        )
        code, out, err = run(c, run_cmd, 120)
        if code != 0:
            print("RUN FAILED:", out, err)
            c.close()
            sys.exit(1)
        print("Container started.")

    # 2. Verify curl localhost:3000
    print("\n=== 2. curl localhost:3000 ===")
    code, out, err = run(c, "sleep 3 && curl -s -o /dev/null -w '%{http_code}' http://localhost:3000", 15)
    http_status = (out + err).strip() or "N/A"
    print("HTTP status:", http_status)

    # 3. Final container status
    print("\n=== 3. Container status ===")
    code, out, err = run(c, "docker ps --filter name=mycosoft-website", 10)
    print(out or err)

    c.close()

    # 4. Cloudflare purge
    print("\n=== 4. Cloudflare purge ===")
    # CODE/WEBSITE/website or CODE/MAS/mycosoft-mas/../WEBSITE/website
    website_root = REPO.parent.parent / "WEBSITE" / "website"
    if not website_root.exists():
        website_root = REPO.parent / "website"
    if website_root.exists():
        sys.path.insert(0, str(website_root))
        try:
            from _cloudflare_cache import purge_everything
            purge_everything()
        except Exception as e:
            print("Cloudflare purge error:", e)
    else:
        print("Website repo not found, skip purge")

    print("\n=== DONE ===")
    print("HTTP result:", http_status)
    sys.exit(0 if http_status == "200" else 1)


if __name__ == "__main__":
    main()
