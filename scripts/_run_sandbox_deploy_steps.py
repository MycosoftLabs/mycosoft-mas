#!/usr/bin/env python3
"""
Sandbox VM (187) website deploy: clean slate, no cache, no half-finished builds.
Kills anything that could block, prunes cache/containers, pulls latest, builds
--no-cache, runs container with NAS mount. Long timeouts so build can finish.
"""
import os
import sys
from pathlib import Path

creds = Path(__file__).resolve().parent.parent / ".credentials.local"
if not creds.exists():
    print("ERROR: .credentials.local not found")
    sys.exit(1)
for line in creds.read_text().splitlines():
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

# Build step often needs 20–40 min on a busy VM
BUILD_TIMEOUT = 2700   # 45 min
PRUNE_TIMEOUT = 120    # 2 min for container prune
BUILDER_PRUNE_TIMEOUT = 600  # 10 min for builder prune (can be slow)
RUN_TIMEOUT = 120      # 2 min for container start

def run(ssh, cmd, timeout=60):
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    try:
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        code = stdout.channel.recv_exit_status()
    except (TimeoutError, Exception) as e:
        out = ""
        err = str(e)
        code = -1
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

    # Step 1: Kill any docker build / buildx so nothing is blocking or wasting memory
    print("\n=== Step 1: Kill all docker build processes ===")
    code, out, err = run(c, "pkill -9 -f 'docker build' 2>/dev/null; pkill -9 -f 'buildkit' 2>/dev/null; echo done", timeout=15)
    results.append(("Kill build", code, out + err))
    print(out or err or f"exit={code}")

    # Step 2: Stop and remove website container (no half-finished state)
    print("\n=== Step 2: Stop and remove website container ===")
    code, out, err = run(c, "docker stop mycosoft-website 2>/dev/null; docker rm mycosoft-website 2>/dev/null; echo done", timeout=30)
    results.append(("Stop/rm website", code, out + err))
    print(out or err or f"exit={code}")

    # Step 3: Prune containers and build cache to free memory/disk
    print("\n=== Step 3: Prune containers ===")
    code, out, err = run(c, "docker container prune -f", timeout=PRUNE_TIMEOUT)
    results.append(("Container prune", code, out + err))
    print(out or err or f"exit={code}")

    print("\n=== Step 4: Prune build cache (no cache, free space) ===")
    try:
        code, out, err = run(c, "docker builder prune -af", timeout=BUILDER_PRUNE_TIMEOUT)
    except Exception as e:
        code, out, err = -1, "", str(e)
    results.append(("Builder prune", code, out + err))
    if code != 0:
        print(out or err or f"exit={code} (continuing anyway)")
    else:
        print(out or err or f"exit={code}")

    # Step 5: Verify no build still running
    print("\n=== Step 5: Verify no docker build running ===")
    code, out, err = run(c, "ps aux | grep -E 'docker build|buildkit' | grep -v grep || echo 'OK: none'", timeout=10)
    results.append(("Verify no build", code, out + err))
    print(out or err or "OK")

    # Step 6: Pull latest and build from scratch (no cache)
    print(f"\n=== Step 6: Fresh build (timeout={BUILD_TIMEOUT}s, ~45 min) ===")
    build_cmd = (
        "cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main && "
        "docker build --network host --no-cache -t mycosoft-always-on-mycosoft-website:latest ."
    )
    code, out, err = run(c, build_cmd, timeout=BUILD_TIMEOUT)
    full_out = out + err
    results.append(("Build", code, full_out))
    if code != 0:
        lines = full_out.strip().split("\n")
        tail = "\n".join(lines[-40:])
        # Avoid UnicodeEncodeError on Windows (cp1252)
        try:
            print(tail)
        except UnicodeEncodeError:
            print(tail.encode("ascii", errors="replace").decode("ascii"))
        print(f"\nBUILD FAILED exit={code}")
    else:
        print("Build succeeded.")

    # Step 7: Run new container with NAS mount
    if code == 0:
        print("\n=== Step 7: Run website container (with NAS mount) ===")
        run_cmd = (
            "docker run -d --name mycosoft-website -p 3000:3000 "
            "-v /opt/mycosoft/media/website/assets:/app/public/assets:ro "
            "-e MAS_API_URL=http://192.168.0.188:8001 --restart unless-stopped "
            "mycosoft-always-on-mycosoft-website:latest"
        )
        code5, out5, err5 = run(c, run_cmd, timeout=RUN_TIMEOUT)
        results.append(("Run container", code5, out5 + err5))
        print(out5 or err5 or f"exit={code5}")

    # Step 8: Verify HTTP
    print("\n=== Step 8: Verify HTTP ===")
    code6, out6, err6 = run(c, "sleep 5 && curl -s -o /dev/null -w '%{http_code}' http://localhost:3000", timeout=15)
    http_status = (out6 + err6).strip() or "N/A"
    results.append(("HTTP check", code6, http_status))
    print(f"HTTP status: {http_status}")

    c.close()

    build_code = next((r[1] for r in results if r[0] == "Build"), -1)

    # Step 8b REMOVED: _sync_nas_push_from_windows.py was deleted (it corrupted NAS and local videos).
    # Upload videos directly to NAS via UniFi web UI; VM mounts the NAS.

    # Step 9: Cloudflare purge (uses CLOUDFLARE_API_TOKEN + CLOUDFLARE_ZONE_ID from website .env.local)
    if build_code == 0 and http_status == "200":
        print("\n=== Step 9: Cloudflare cache purge ===")
        try:
            website_root = Path(__file__).resolve().parent.parent.parent.parent / "WEBSITE" / "website"
            if not website_root.is_dir():
                website_root = Path(__file__).resolve().parent.parent.parent.parent / "website"
            if website_root.is_dir():
                sys.path.insert(0, str(website_root))
                from _cloudflare_cache import purge_everything
                purge_everything()
            else:
                print("Cloudflare purge skipped: website repo not found (set CLOUDFLARE_* in env to purge)")
        except ImportError as e:
            print(f"Cloudflare purge skipped: {e}")
        except Exception as e:
            print(f"Cloudflare purge error: {e}")

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for name, ec, txt in results:
        tail = (txt[:200] + "..." if len(txt) > 200 else txt).replace("\n", " ")
        safe = tail[:80].encode("ascii", errors="replace").decode("ascii")
        print(f"  {name}: exit={ec} | {safe}")
    print(f"\nBuild exit code: {build_code}")
    print(f"Final HTTP status: {http_status}")
    if build_code != 0:
        print("\nLast 40 lines of build output:")
        build_result = next((r[2] for r in results if r[0] == "Build"), "")
        tail = "\n".join(build_result.strip().split("\n")[-40:])
        try:
            print(tail)
        except UnicodeEncodeError:
            print(tail.encode("ascii", errors="replace").decode("ascii"))
    sys.exit(0 if build_code == 0 and http_status == "200" else 1)

if __name__ == "__main__":
    main()
