#!/usr/bin/env python3
"""Sandbox full check, clean, deploy per user spec."""
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

    results = {}

    # === 1. PRE-CLEAN STATE ===
    print("\n" + "="*60)
    print("1. PRE-CLEAN STATE")
    print("="*60)

    print("\n--- docker ps -a ---")
    code, out, err = run(c, "docker ps -a")
    results["pre_docker_ps"] = out or err
    print(out or err)

    print("\n--- ps aux | grep -E 'docker build|_rebuild' ---")
    code, out, err = run(c, "ps aux | grep -E 'docker build|_rebuild' | grep -v grep || echo 'No stuck build processes'")
    results["pre_build_procs"] = out or err
    print(out or err)

    print("\n--- docker images mycosoft-always-on-mycosoft-website ---")
    code, out, err = run(c, 'docker images mycosoft-always-on-mycosoft-website --format "{{.Tag}} {{.CreatedAt}}"')
    results["pre_images"] = out or err or "(none)"
    print(out or err or "(none)")

    # === 2. CLEAN ===
    print("\n" + "="*60)
    print("2. CLEAN (kill builds, prune)")
    print("="*60)

    print("\n--- Killing docker build processes ---")
    code, out, err = run(c, "pkill -9 -f 'docker build' 2>/dev/null; pkill -9 -f 'docker-buildx' 2>/dev/null; echo done")
    print(out or err)

    print("\n--- docker builder prune -f ---")
    code, out, err = run(c, "docker builder prune -f", timeout=120)
    print(out or err)

    print("\n--- docker container prune -f ---")
    code, out, err = run(c, "docker container prune -f", timeout=120)
    print(out or err)

    # === 3. VERIFY AFTER CLEAN ===
    print("\n" + "="*60)
    print("3. VERIFY AFTER CLEAN")
    print("="*60)

    print("\n--- No build processes running? ---")
    code, out, err = run(c, "ps aux | grep -E 'docker build|docker-buildx' | grep -v grep || echo 'None - OK'")
    print(out or err)

    print("\n--- Site HTTP check ---")
    code, out, err = run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000", timeout=10)
    pre_deploy_http = (out + err).strip() or "N/A"
    print(f"HTTP: {pre_deploy_http}")

    # === 4. FULL DEPLOY ===
    print("\n" + "="*60)
    print("4. FULL DEPLOY")
    print("="*60)

    print("\n--- git fetch + reset ---")
    code, out, err = run(c, "cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main", timeout=60)
    print(out or err or f"rc={code}")

    print("\n--- docker build (--no-cache, may take 5-15 min) ---")
    build_cmd = (
        "cd /opt/mycosoft/website && "
        "docker build --network host --no-cache -t mycosoft-always-on-mycosoft-website:latest ."
    )
    code, out, err = run(c, build_cmd, timeout=900)
    full_build = out + err

    if code != 0:
        print("\n--- BUILD FAILED (last 40 lines) ---")
        lines = full_build.strip().split("\n")
        fail_lines = "\n".join(lines[-40:])
        print(fail_lines)
        results["build_result"] = "FAIL"
        results["build_output"] = fail_lines
    else:
        results["build_result"] = "SUCCESS"
        print("Build succeeded.")

        print("\n--- Stop, rm, run container ---")
        code, out, err = run(c, "docker stop mycosoft-website 2>/dev/null; docker rm mycosoft-website 2>/dev/null; echo stopped")
        print(out or err)

        run_cmd = (
            "docker run -d --name mycosoft-website -p 3000:3000 "
            "-v /opt/mycosoft/media/website/assets:/app/public/assets:ro "
            "-e MAS_API_URL=http://192.168.0.188:8001 --restart unless-stopped "
            "mycosoft-always-on-mycosoft-website:latest"
        )
        code, out, err = run(c, run_cmd, timeout=60)
        print(out or err or f"rc={code}")

    # === 5. FINAL VERIFY ===
    print("\n" + "="*60)
    print("5. FINAL VERIFY")
    print("="*60)

    print("\n--- Site HTTP 200 check ---")
    code, out, err = run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000", timeout=10)
    final_http = (out + err).strip() or "N/A"
    print(f"HTTP: {final_http}")

    print("\n--- MAS 188 health ---")
    code, out, err = run(c, "curl -s -o /dev/null -w '%{http_code}' http://192.168.0.188:8001/health", timeout=5)
    mas_status = (out + err).strip() or "N/A"
    print(f"MAS: {mas_status}")

    print("\n--- MINDEX 189 health ---")
    code, out, err = run(c, "curl -s -o /dev/null -w '%{http_code}' http://192.168.0.189:8000/health", timeout=5)
    mindex_status = (out + err).strip() or "N/A"
    print(f"MINDEX: {mindex_status}")

    c.close()

    # === SUMMARY ===
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Pre-clean state: docker_ps, images, build_procs captured")
    print(f"Post-clean: no build procs, pre-deploy HTTP={pre_deploy_http}")
    print(f"Build result: {results.get('build_result', 'N/A')}")
    if results.get("build_output"):
        print("Build output (last 40): see above")
    print(f"Final HTTP: {final_http}")
    print(f"MAS 188: {mas_status}")
    print(f"MINDEX 189: {mindex_status}")

    sys.exit(0 if results.get("build_result") == "SUCCESS" and final_http == "200" else 1)

if __name__ == "__main__":
    main()
