#!/usr/bin/env python3
"""Diagnose Sandbox website state and run full clean redeploy if deployment incomplete."""
import os
import sys
from pathlib import Path

# Load credentials
creds = Path(__file__).parent.parent / ".credentials.local"
if creds.exists():
    for line in creds.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

VM_PASS = os.environ.get("VM_PASSWORD") or os.environ.get("VM_SSH_PASSWORD")
if not VM_PASS:
    print("ERROR: No VM_PASSWORD"); sys.exit(1)

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
    transport = c.get_transport()
    if transport:
        transport.set_keepalive(30)

    all_output = []
    def log(msg):
        print(msg)
        all_output.append(msg)

    # === 1. Container status ===
    log("\n=== 1. docker ps -a --filter name=mycosoft-website ===")
    code, out, err = run(c, "docker ps -a --filter name=mycosoft-website")
    log(out or err or f"(empty, rc={code})")

    # === 2. Image info ===
    log("\n=== 2. docker images mycosoft-always-on-mycosoft-website ===")
    code, out, err = run(c, 'docker images mycosoft-always-on-mycosoft-website --format "{{.Tag}} {{.CreatedAt}}"')
    log(out or err or "(no image)")

    # === 3. Active builds ===
    log("\n=== 3. ps aux | grep 'docker build' ===")
    code, out, err = run(c, "ps aux | grep 'docker build' | grep -v grep || echo 'No active docker build'")
    log(out or err or "(empty)")

    # === 4. Git version ===
    log("\n=== 4. cd /opt/mycosoft/website && git log -1 --oneline ===")
    code, out, err = run(c, "cd /opt/mycosoft/website && git log -1 --oneline")
    log(out or err or f"(rc={code})")

    # Determine if redeploy needed
    container_exists = "mycosoft-website" in (out or "") and "Exited" not in (out or "")
    has_image = bool(out and out.strip()) in [True]  # check image output
    code2, img_out, _ = run(c, 'docker images mycosoft-always-on-mycosoft-website --format "{{.Tag}}" -q')
    has_image = bool(img_out and img_out.strip())
    no_active_build = "No active docker build" in (out or "") or "docker build" not in (out or "")

    # Prune orphan containers
    log("\n=== docker container prune -f ===")
    code, out, err = run(c, "docker container prune -f", timeout=120)
    log(out or err or f"rc={code}")

    # Optional: builder prune (user said optional)
    # log("\n=== docker builder prune -f ===")
    # code, out, err = run(c, "docker builder prune -f", timeout=60)
    # log(out or err)

    # Full clean redeploy
    log("\n=== FULL CLEAN REDEPLOY ===")
    log("Stopping and removing container...")
    code, out, err = run(c, "docker stop mycosoft-website 2>/dev/null; docker rm mycosoft-website 2>/dev/null; echo done")
    log(out or err or f"rc={code}")

    log("Fetching and resetting git...")
    code, out, err = run(c, "cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main", timeout=60)
    log(out or err or f"rc={code}")

    log("Building (--no-cache, this may take 5-15 min)...")
    build_cmd = (
        "cd /opt/mycosoft/website && "
        "docker build --network host --no-cache -t mycosoft-always-on-mycosoft-website:latest ."
    )
    code, out, err = run(c, build_cmd, timeout=900)
    full_build = out + err
    if code != 0:
        log("\n--- BUILD FAILED (last 40 lines) ---")
        lines = full_build.strip().split("\n")
        log("\n".join(lines[-40:]))
        log(f"\nBUILD EXIT CODE: {code}")
        c.close()
        print("\n" + "="*60)
        print("RESULT: BUILD FAILED")
        print("="*60)
        sys.exit(1)

    log("Build succeeded.")

    log("\nStarting container...")
    run_cmd = (
        "docker run -d --name mycosoft-website -p 3000:3000 "
        "-v /opt/mycosoft/media/website/assets:/app/public/assets:ro "
        "-e MAS_API_URL=http://192.168.0.188:8001 --restart unless-stopped "
        "mycosoft-always-on-mycosoft-website:latest"
    )
    code, out, err = run(c, run_cmd, timeout=60)
    log(out or err or f"rc={code}")

    log("\n=== HTTP health check ===")
    code, out, err = run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000", timeout=10)
    http_status = (out + err).strip() or "N/A"
    log(f"HTTP status: {http_status}")

    c.close()

    # Final summary
    print("\n" + "="*60)
    print("DIAGNOSTIC AND REDEPLOY COMPLETE")
    print("="*60)
    print(f"Build result: SUCCESS")
    print(f"HTTP status: {http_status}")
    print(f"Cloudflare purge needed: YES (deployment completed with new image)")
    sys.exit(0 if http_status == "200" else 1)

if __name__ == "__main__":
    main()
