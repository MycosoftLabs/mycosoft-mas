#!/usr/bin/env python3
"""
Full MAS Deployment Script - Deploys latest code to VM 188 and restarts MAS orchestrator.
FEB 10, 2026
"""

import subprocess
import sys
import time
import os

# Paramiko for SSH
try:
    import paramiko
except ImportError:
    print("Installing paramiko...")
    subprocess.run([sys.executable, "-m", "pip", "install", "paramiko", "-q"])
    import paramiko

# VM Configuration - Load credentials from environment
VM_188 = os.environ.get("MAS_VM_IP", "192.168.0.188")
SSH_USER = os.environ.get("VM_USER", "mycosoft")
SSH_PASS = os.environ.get("VM_PASSWORD")

if not SSH_PASS:
    print("ERROR: VM_PASSWORD environment variable is not set.")
    print("Please set it before running this script:")
    print("  $env:VM_PASSWORD = 'your-password'  # PowerShell")
    print("  export VM_PASSWORD='your-password'  # Bash")
    sys.exit(1)

# Mycorrhizae API Key for MAS
MAS_MYCORRHIZAE_KEY = "myco_mas_kck8lD0E8sPvfob_EQS4xnuuj5h1WB7Ss72Y8xoz9QQ"

# LLM API Keys for MYCA Consciousness - loaded from environment variables
# Set these in your environment before running this script:
#   ANTHROPIC_API_KEY, OPENAI_API_KEY, GROQ_API_KEY, GEMINI_API_KEY, XAI_API_KEY
import os
LLM_API_KEYS = {
    "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
    "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
    "GROQ_API_KEY": os.environ.get("GROQ_API_KEY", ""),
    "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", ""),
    "XAI_API_KEY": os.environ.get("XAI_API_KEY", ""),
}


def ssh_exec(host: str, cmd: str, timeout: int = 120) -> tuple:
    """Execute SSH command and return (stdout, stderr, exit_code)"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=SSH_USER, password=SSH_PASS, timeout=30)
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        code = stdout.channel.recv_exit_status()
        return out, err, code
    finally:
        client.close()


def main():
    print("=" * 60)
    print("FULL MAS DEPLOYMENT TO VM 188")
    print("=" * 60)
    
    # Step 1: Check if git is clean on VM and pull latest
    print("\n[1/5] Pulling latest code on VM 188...")
    out, err, code = ssh_exec(VM_188, """
cd /home/mycosoft/mycosoft/mas
git fetch origin
git reset --hard origin/main
git log -1 --oneline
""")
    print(out)
    if code != 0:
        print(f"[WARN] Git pull had issues: {err}")
    
    # Step 2: Verify critical file exists
    print("\n[2/5] Verifying iot_envelope_api.py exists...")
    out, err, code = ssh_exec(VM_188, """
ls -la /home/mycosoft/mycosoft/mas/mycosoft_mas/core/routers/iot_envelope_api.py 2>/dev/null || echo "FILE_NOT_FOUND"
""")
    if "FILE_NOT_FOUND" in out:
        print("[ERROR] iot_envelope_api.py not found after pull!")
        print("The file may not be pushed to GitHub yet.")
        print("Please run: git add . && git commit -m 'Add IoT envelope API' && git push")
        sys.exit(1)
    print(out.strip())
    print("[OK] Critical file exists")
    
    # Step 3: Stop current MAS container
    print("\n[3/5] Stopping current MAS container...")
    out, err, code = ssh_exec(VM_188, """
docker stop myca-orchestrator-new 2>/dev/null || true
docker rm myca-orchestrator-new 2>/dev/null || true
docker ps -a | grep myca
""")
    print(out if out.strip() else "Container stopped/removed")
    
    # Step 4: Rebuild Docker image
    print("\n[4/5] Rebuilding MAS Docker image (this takes a few minutes)...")
    out, err, code = ssh_exec(VM_188, """
cd /home/mycosoft/mycosoft/mas
docker build -t mycosoft/mas-agent:latest --no-cache . 2>&1 | tail -20
""", timeout=600)  # 10 minute timeout for build
    print(out)
    if code != 0:
        print(f"[ERROR] Docker build failed: {err}")
        sys.exit(1)
    print("[OK] Docker image rebuilt")
    
    # Step 5: Start MAS with Mycorrhizae configuration and LLM keys
    print("\n[5/5] Starting MAS container with Mycorrhizae API and LLM keys...")
    
    # Build environment variable arguments for LLM keys
    llm_env_args = " \\\n  ".join([f"-e {k}={v}" for k, v in LLM_API_KEYS.items()])
    
    out, err, code = ssh_exec(VM_188, f"""
docker run -d --name myca-orchestrator-new \\
  --restart unless-stopped \\
  --network host \\
  -e MYCORRHIZAE_API_URL=http://127.0.0.1:8002 \\
  -e MYCORRHIZAE_API_KEY={MAS_MYCORRHIZAE_KEY} \\
  -e DATABASE_URL=postgresql://mycosoft:REDACTED_DB_PASSWORD@192.168.0.189:5432/mindex \\
  -e REDIS_URL=redis://192.168.0.189:6379/0 \\
  -e N8N_URL=http://192.168.0.188:5678 \\
  -e MINDEX_API_URL=http://192.168.0.189:8000 \\
  -e ANTHROPIC_API_KEY={LLM_API_KEYS['ANTHROPIC_API_KEY']} \\
  -e OPENAI_API_KEY={LLM_API_KEYS['OPENAI_API_KEY']} \\
  -e GROQ_API_KEY={LLM_API_KEYS['GROQ_API_KEY']} \\
  -e GEMINI_API_KEY={LLM_API_KEYS['GEMINI_API_KEY']} \\
  -e XAI_API_KEY={LLM_API_KEYS['XAI_API_KEY']} \\
  mycosoft/mas-agent:latest

sleep 3
docker ps | grep myca
""")
    print(out)
    if "myca-orchestrator-new" not in out:
        print(f"[ERROR] Container failed to start: {err}")
        out2, _, _ = ssh_exec(VM_188, "docker logs myca-orchestrator-new 2>&1 | tail -30")
        print("Recent logs:")
        print(out2)
        sys.exit(1)
    
    # Wait for health check (port 8000 with --network host)
    print("\n[+] Waiting for MAS to become healthy...")
    for i in range(10):
        time.sleep(3)
        out, err, code = ssh_exec(VM_188, "curl -s http://127.0.0.1:8000/health 2>/dev/null || echo 'NOT_READY'")
        if "NOT_READY" not in out and "error" not in out.lower():
            print(f"[OK] MAS is healthy: {out.strip()}")
            break
        print(f"  Attempt {i+1}/10: {out.strip()[:50]}...")
    else:
        print("[WARN] MAS health check still failing after 30 seconds")
        out, _, _ = ssh_exec(VM_188, "docker logs myca-orchestrator-new 2>&1 | tail -50")
        print("Recent logs:")
        print(out)
    
    # Final verification
    print("\n" + "=" * 60)
    print("DEPLOYMENT SUMMARY")
    print("=" * 60)
    out, err, code = ssh_exec(VM_188, """
echo "MAS Container Status:"
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'NAMES|myca'

echo ""
echo "Mycorrhizae Container Status:"
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'NAMES|mycorrhizae'

echo ""
echo "Health Check Results:"
echo "  MAS:         $(curl -s http://127.0.0.1:8000/health 2>/dev/null | head -c 100 || echo 'FAILED')"
echo "  Mycorrhizae: $(curl -s http://127.0.0.1:8002/health 2>/dev/null | head -c 100 || echo 'FAILED')"
echo ""
echo "MYCA Consciousness Status:"
curl -s http://127.0.0.1:8000/api/myca/status 2>/dev/null | head -c 200 || echo 'NOT AVAILABLE'
""")
    print(out)
    
    print("\n[DONE] Full MAS deployment complete!")
    print(f"\nMAS API: http://192.168.0.188:8000 (internal: 127.0.0.1:8000)")
    print(f"Mycorrhizae API: http://192.168.0.188:8002")
    print(f"MYCA Consciousness: http://192.168.0.188:8000/api/myca/*")


if __name__ == "__main__":
    main()
