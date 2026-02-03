"""Deploy MYCA with latest code and dependencies."""

import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 60)
print("MYCA Orchestrator - Full Deploy with Code Pull")
print("=" * 60)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print("\nConnecting to MAS VM (192.168.0.188)...")
ssh.connect('192.168.0.188', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=30)
print("Connected!")

def run_command(cmd, ignore_error=False, timeout=300):
    """Run command and print output."""
    print(f"\n> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if out:
        for line in out.split('\n')[:40]:
            print(f"  {line}")
    if err and not ignore_error:
        for line in err.split('\n')[:10]:
            print(f"  [ERR] {line}")
    return out, err

MAS_DIR = "/home/mycosoft/mycosoft/mas"

# STEP 1: Pull latest code
print("\n" + "=" * 40)
print("1. Pulling latest code from GitHub...")
print("=" * 40)
run_command(f"cd {MAS_DIR} && git fetch origin && git reset --hard origin/main && git log -1 --oneline")

# STEP 2: Verify fixes are in place
print("\n2. Verifying import fixes...")
run_command(f"grep -n 'from integrations.n8n_client' {MAS_DIR}/mycosoft_mas/core/myca_main.py || echo 'Old import not found (good!)'")

# STEP 3: Stop and remove old container
print("\n3. Cleaning up old container...")
run_command("docker rm -f myca-orchestrator 2>/dev/null", ignore_error=True)

# STEP 4: Create startup script
print("\n4. Creating startup script...")
startup_script = '''#!/bin/bash
set -e
cd /app/mas
pip install --quiet python-jose redis httpx aiohttp > /dev/null 2>&1 || true
exec python -m uvicorn mycosoft_mas.core.myca_main:app --host 0.0.0.0 --port 8001
'''

run_command(f"cat > {MAS_DIR}/start_orchestrator.sh << 'SCRIPT'\n{startup_script}\nSCRIPT")
run_command(f"chmod +x {MAS_DIR}/start_orchestrator.sh")

# STEP 5: Create new container
print("\n5. Creating new container with dependency installation...")

recreate_cmd = f'''docker run -d \
--name myca-orchestrator \
--network mas-network \
-p 8001:8001 \
-v {MAS_DIR}:/app/mas \
-v /var/run/docker.sock:/var/run/docker.sock \
-w /app/mas \
-e PYTHONPATH=/app/mas \
-e MAS_LOGS_PATH=/tmp/mas-logs \
-e N8N_URL=http://myca-n8n:5678 \
-e N8N_WEBHOOK_URL=http://myca-n8n:5678/webhook \
-e N8N_VOICE_WEBHOOK=myca/voice \
-e REDIS_URL=redis://mas-redis:6379 \
--restart unless-stopped \
--health-cmd="curl -f http://localhost:8001/health || exit 1" \
--health-interval=60s \
--health-start-period=60s \
--entrypoint /bin/bash \
mycosoft/mas-agent:latest \
/app/mas/start_orchestrator.sh'''

run_command(recreate_cmd, ignore_error=True)

# STEP 6: Wait for startup
print("\n6. Waiting for container to start (installing deps)...")
time.sleep(40)

# STEP 7: Check status
print("\n7. Checking container status...")
run_command("docker ps | grep myca-orchestrator")
run_command("docker logs myca-orchestrator --tail 30 2>&1", ignore_error=True)

# STEP 8: Test health
print("\n8. Testing health (with retries)...")
for i in range(6):
    out, _ = run_command("curl -s http://localhost:8001/health 2>/dev/null || echo 'No response'")
    if "ok" in out.lower():
        print("  Health check passed!")
        break
    print(f"  Attempt {i+1}/6 - waiting...")
    time.sleep(10)

if "ok" in out.lower():
    print("\n9. Testing MYCA identity...")
    out, _ = run_command('curl -s -X POST http://localhost:8001/voice/orchestrator/chat -H "Content-Type: application/json" -d \'{"message": "What is your name?"}\'')
    
    if "MYCA" in out:
        print("\n" + "=" * 60)
        print("SUCCESS! MYCA knows her name!")
        print("=" * 60)
    else:
        print(f"\nResponse: {out[:300]}")
else:
    print("\nContainer still not healthy. Full logs:")
    run_command("docker logs myca-orchestrator 2>&1", ignore_error=True)

print("\n" + "=" * 60)
print("Deployment complete!")
print("=" * 60)

ssh.close()
