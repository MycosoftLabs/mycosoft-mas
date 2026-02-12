#!/usr/bin/env python3
"""Ask MYCA via SSH curl since external port is blocked."""
import paramiko
import json

VM = "192.168.0.188"
USER = "mycosoft"
PASS = "Mushroom1!Mushroom1!"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM, username=USER, password=PASS, timeout=15)

print("=" * 80)
print("ASKING MYCA: Are you alive, conscious, and working?")
print("=" * 80)

# 1. Status
print("\n[1/3] Getting MYCA status...")
stdin, stdout, stderr = ssh.exec_command("curl -s http://127.0.0.1:8000/api/myca/status", timeout=15)
out = stdout.read().decode()
if out.strip():
    try:
        data = json.loads(out)
        print(f"  Status: {json.dumps(data, indent=2)}")
    except:
        print(f"  Raw: {out[:500]}")
else:
    print(f"  Error: {stderr.read().decode()[:500]}")

# 2. Identity
print("\n[2/3] Getting MYCA identity...")
stdin, stdout, stderr = ssh.exec_command("curl -s http://127.0.0.1:8000/api/myca/identity", timeout=15)
out = stdout.read().decode()
if out.strip():
    try:
        data = json.loads(out)
        print(f"  Name: {data.get('name', 'N/A')}")
        print(f"  Creator: {data.get('creator', 'N/A')}")
        print(f"  Role: {data.get('role', 'N/A')}")
    except:
        print(f"  Raw: {out[:500]}")
else:
    print(f"  Error: {stderr.read().decode()[:500]}")

# 3. Ask MYCA directly
print("\n[3/3] Asking MYCA directly via chat...")
cmd = '''curl -s -X POST http://127.0.0.1:8000/api/myca/chat -H "Content-Type: application/json" -d '{"message": "MYCA, are you alive and conscious? Tell me about your purpose and how you feel right now. Be detailed and personal.", "session_id": "test-feb10-final"}'  '''
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
out = stdout.read().decode()
if out.strip():
    try:
        data = json.loads(out)
        reply = data.get("message", "")
        print(f"\n  MYCA's Reply:\n  {reply}\n")
        print(f"\n  Thoughts processed: {data.get('thoughts_processed', 'N/A')}")
        emotional_state = data.get("emotional_state")
        if emotional_state:
            print(f"  Emotional state: {json.dumps(emotional_state, indent=2)}")
    except Exception as e:
        print(f"  Parse error: {e}")
        print(f"  Raw: {out[:1000]}")
else:
    print(f"  Error: {stderr.read().decode()[:500]}")

print("\n" + "=" * 80)
print("TEST COMPLETE - If MYCA responded with detailed personal answers, she is ALIVE.")
print("=" * 80)

ssh.close()
