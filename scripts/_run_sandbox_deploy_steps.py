#!/usr/bin/env python3
"""One-off: Run exact deploy steps on Sandbox VM and report results."""
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

    results = []

    # Step 1: Kill docker build
    print("\n=== Step 1: Kill docker build ===")
    code, out, err = run(c, "pkill -9 -f 'docker build' 2>/dev/null || true; echo done")
    results.append(("Step 1 (kill)", code, out + err))
    print(out or err or f"exit={code}")

    # Step 2: Prune
    print("\n=== Step 2: Prune containers ===")
    code, out, err = run(c, "docker container prune -f", timeout=120)
    results.append(("Step 2 (prune)", code, out + err))
    print(out or err or f"exit={code}")

    # Step 3: Verify no build
    print("\n=== Step 3: Verify no docker build ===")
    code, out, err = run(c, "ps aux | grep 'docker build' | grep -v grep || echo 'OK: none'")
    results.append(("Step 3 (verify)", code, out + err))
    print(out or err or "OK")

    # Step 4: Build (long timeout)
    print("\n=== Step 4: Fresh build (this may take 5-15 min) ===")
    build_cmd = (
        "cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main && "
        "docker build --network host --no-cache -t mycosoft-always-on-mycosoft-website:latest ."
    )
    code, out, err = run(c, build_cmd, timeout=900)  # 15 min
    full_out = out + err
    results.append(("Step 4 (build)", code, full_out))
    if code != 0:
        lines = full_out.strip().split("\n")
        print("\n".join(lines[-30:]))
        print(f"\nBUILD FAILED exit={code}")
    else:
        print("Build succeeded.")

    # Step 5: Stop, rm, run
    if code == 0:
        print("\n=== Step 5: Stop/rm/run container ===")
        run_cmd = (
            "docker stop mycosoft-website 2>/dev/null; docker rm mycosoft-website 2>/dev/null; "
            "docker run -d --name mycosoft-website -p 3000:3000 "
            "-v /opt/mycosoft/media/website/assets:/app/public/assets:ro "
            "-e MAS_API_URL=http://192.168.0.188:8001 --restart unless-stopped "
            "mycosoft-always-on-mycosoft-website:latest"
        )
        code5, out5, err5 = run(c, run_cmd, timeout=60)
        results.append(("Step 5 (run)", code5, out5 + err5))
        print(out5 or err5 or f"exit={code5}")

    # Step 6: Verify HTTP
    print("\n=== Step 6: Verify HTTP ===")
    code6, out6, err6 = run(c, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000", timeout=10)
    http_status = (out6 + err6).strip() or "N/A"
    results.append(("Step 6 (curl)", code6, http_status))
    print(f"HTTP status: {http_status}")

    c.close()

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for name, ec, txt in results:
        tail = (txt[:200] + "..." if len(txt) > 200 else txt).replace("\n", " ")
        print(f"{name}: exit={ec} | {tail[:80]}")
    build_code = next(r[1] for r in results if "build" in r[0].lower())
    print(f"\nBuild exit code: {build_code}")
    print(f"Final HTTP status: {http_status}")
    if build_code != 0:
        print("\nLast 30 lines of build output:")
        lines = results[3][2].strip().split("\n")
        print("\n".join(lines[-30:]))
    sys.exit(0 if build_code == 0 and http_status == "200" else 1)

if __name__ == "__main__":
    main()
