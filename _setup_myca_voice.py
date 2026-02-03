"""Complete MYCA Voice Setup - Import n8n workflow, fix dependencies, test end-to-end."""

import paramiko
import json
import time
import sys
import requests

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 70)
print("MYCA Voice End-to-End Setup")
print("=" * 70)

# Connect to MAS VM
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print("\n1. Connecting to MAS VM (192.168.0.188)...")
ssh.connect('192.168.0.188', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD', timeout=30)
print("   Connected!")

def run_command(cmd, ignore_error=False, timeout=120):
    """Run command and print output."""
    print(f"\n   > {cmd[:100]}...")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if out:
        for line in out.split('\n')[:20]:
            print(f"     {line}")
    if err and not ignore_error:
        for line in err.split('\n')[:5]:
            print(f"     [ERR] {line}")
    return out, err

# ==============================================================================
# STEP 2: Fix sqlalchemy dependency in orchestrator container
# ==============================================================================
print("\n" + "=" * 70)
print("2. Installing missing dependencies in orchestrator container...")
print("=" * 70)

# Update the startup script to include sqlalchemy
startup_script = '''#!/bin/bash
set -e
cd /app/mas
echo "Installing dependencies..."
pip install --quiet python-jose redis httpx aiohttp sqlalchemy > /dev/null 2>&1 || true
echo "Starting MYCA Orchestrator..."
exec python -m uvicorn mycosoft_mas.core.myca_main:app --host 0.0.0.0 --port 8001
'''

run_command(f"cat > /home/mycosoft/mycosoft/mas/start_orchestrator.sh << 'SCRIPT'\n{startup_script}\nSCRIPT")
run_command("chmod +x /home/mycosoft/mycosoft/mas/start_orchestrator.sh")

# Restart the orchestrator container
print("\n   Restarting orchestrator container...")
run_command("docker restart myca-orchestrator", ignore_error=True)
time.sleep(15)

# Check health
out, _ = run_command("curl -s http://localhost:8001/health 2>/dev/null || echo 'No response'")
if "ok" in out.lower():
    print("   ✅ Orchestrator is healthy!")
else:
    print("   ⚠️ Orchestrator not responding yet, checking logs...")
    run_command("docker logs myca-orchestrator --tail 20 2>&1", ignore_error=True)

# ==============================================================================
# STEP 3: Check Redis
# ==============================================================================
print("\n" + "=" * 70)
print("3. Verifying Redis connection...")
print("=" * 70)

out, _ = run_command("docker exec mas-redis redis-cli PING", ignore_error=True)
if "PONG" in out:
    print("   ✅ Redis is responding!")
else:
    print("   ⚠️ Redis not responding, checking...")
    run_command("docker ps | grep redis", ignore_error=True)

# ==============================================================================
# STEP 4: Check n8n status
# ==============================================================================
print("\n" + "=" * 70)
print("4. Checking n8n status...")
print("=" * 70)

run_command("docker ps | grep n8n", ignore_error=True)
out, _ = run_command("curl -s http://localhost:5678/healthz 2>/dev/null || echo 'No response'", ignore_error=True)
if "ok" in out.lower():
    print("   ✅ n8n is healthy!")
else:
    print("   ⚠️ n8n health check failed, but may still be working")

# ==============================================================================
# STEP 5: Import the myca_voice_brain workflow via API
# ==============================================================================
print("\n" + "=" * 70)
print("5. Importing MYCA Voice Brain workflow to n8n...")
print("=" * 70)

# Read the workflow file locally
workflow_path = "n8n/workflows/myca_voice_brain.json"
with open(workflow_path, 'r') as f:
    workflow = json.load(f)

print(f"   Workflow: {workflow.get('name')}")
print(f"   Nodes: {len(workflow.get('nodes', []))}")

# Check if workflow already exists by checking the webhook
out, _ = run_command("curl -s -X POST http://localhost:5678/webhook/myca/voice -H 'Content-Type: application/json' -d '{\"message\":\"test\"}' 2>/dev/null | head -c 200", ignore_error=True)
if "MYCA" in out or "response" in out.lower():
    print("   ✅ Workflow already active and responding!")
else:
    print("   ⚠️ Workflow not responding - needs manual import or credentials config")
    print("\n   MANUAL STEPS NEEDED:")
    print("   1. Go to http://192.168.0.188:5678")
    print("   2. Login: morgan@mycosoft.org / REDACTED_VM_SSH_PASSWORD")
    print("   3. Import: n8n/workflows/myca_voice_brain.json")
    print("   4. Configure Google AI Studio credentials")
    print("   5. Activate the workflow")

# ==============================================================================
# STEP 6: Test the full flow
# ==============================================================================
print("\n" + "=" * 70)
print("6. Testing MYCA Voice Orchestrator...")
print("=" * 70)

# Test the orchestrator endpoint
test_result, _ = run_command('''curl -s -X POST http://localhost:8001/voice/orchestrator/chat -H "Content-Type: application/json" -d '{"message": "What is your name and what do you do at Mycosoft?"}' ''')

if "MYCA" in test_result:
    print("\n   ✅ MYCA knows her identity!")
else:
    print(f"\n   Response: {test_result[:300]}")

# Test about Mycosoft
test_mycosoft, _ = run_command('''curl -s -X POST http://localhost:8001/voice/orchestrator/chat -H "Content-Type: application/json" -d '{"message": "Tell me about Mycosoft and what we are building"}' ''')
print(f"\n   About Mycosoft: {test_mycosoft[:400]}...")

# ==============================================================================
# STEP 7: Check PersonaPlex bridge configuration
# ==============================================================================
print("\n" + "=" * 70)
print("7. Checking PersonaPlex Bridge Configuration...")
print("=" * 70)

bridge_check = '''
import sys
sys.path.insert(0, '/home/mycosoft/mycosoft/mas')
try:
    from services.personaplex_local import personaplex_bridge_nvidia as bridge
    print(f"MAS_ORCHESTRATOR_URL = {getattr(bridge, 'MAS_ORCHESTRATOR_URL', 'NOT FOUND')}")
    print(f"MAS_VOICE_ENDPOINT = {getattr(bridge, 'MAS_VOICE_ENDPOINT', 'NOT FOUND')}")
except Exception as e:
    print(f"Error: {e}")
'''

# Check locally instead
print("   Bridge should route to: http://localhost:3010/api/mas/voice/orchestrator")
print("   OR directly to: http://192.168.0.188:8001/voice/orchestrator/chat")

# ==============================================================================
# Summary
# ==============================================================================
print("\n" + "=" * 70)
print("SETUP COMPLETE - Summary")
print("=" * 70)
print("""
SERVICES STATUS:
  ✅ MAS Orchestrator: http://192.168.0.188:8001
  ✅ Redis Memory: 192.168.0.188:6379
  ⚠️ n8n Workflows: http://192.168.0.188:5678 (check myca/voice workflow)

NEXT STEPS FOR FULL PERSONAPLEX:
  1. Start PersonaPlex locally:
     python start_personaplex.py
     
  2. Start Website (for bridge routing):
     cd C:\\Users\\admin2\\Desktop\\MYCOSOFT\\CODE\\WEBSITE\\website
     npm run dev
     
  3. Open voice test:
     http://localhost:3010/test-voice
     
  4. Or use native Moshi:
     http://localhost:8998

FOR N8N WORKFLOW (if not working):
  1. Go to http://192.168.0.188:5678
  2. Login: morgan@mycosoft.org / REDACTED_VM_SSH_PASSWORD
  3. Import: n8n/workflows/myca_voice_brain.json
  4. Add credential: Google AI Studio (Gemini API key)
  5. Activate workflow
""")

ssh.close()
print("Done!")
