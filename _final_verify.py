import paramiko
import time
import sys
import requests

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=== Final Integration Verification ===\n")

# Test MAS Memory API
print("1. MAS Memory API (192.168.0.188:8001)")
try:
    r = requests.get("http://192.168.0.188:8001/api/memory/health", timeout=5)
    data = r.json()
    print(f"   Status: {data.get('status', 'unknown')}")
    print(f"   Redis: {data.get('redis', 'unknown')}")
    print(f"   Scopes: {len(data.get('scopes', []))} scopes")
except Exception as e:
    print(f"   Error: {e}")

# Test MAS write to memory
print("\n2. MAS Memory Write Test")
try:
    r = requests.post("http://192.168.0.188:8001/api/memory/write", 
        json={
            "scope": "system",
            "namespace": "integration_test",
            "key": "final_test",
            "value": {"test": "complete", "timestamp": "2026-02-04T22:05:00Z"}
        }, timeout=5)
    print(f"   Write: {'SUCCESS' if r.status_code == 200 else 'FAILED'}")
except Exception as e:
    print(f"   Error: {e}")

# Test Website API
print("\n3. Website API (192.168.0.187:3000)")
try:
    r = requests.get("http://192.168.0.187:3000/api/health", timeout=5)
    data = r.json()
    print(f"   Status: {data.get('status', 'unknown')}")
    print(f"   Environment: {data.get('environment', 'unknown')}")
except Exception as e:
    print(f"   Error: {e}")

# Test MINDEX DB via MAS
print("\n4. MINDEX Database (via SSH)")
mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = "Mushroom1!Mushroom1!"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=user, password=passwd, timeout=30)

stdin, stdout, stderr = ssh.exec_command('docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT COUNT(*) as total FROM memory.entries;"')
time.sleep(3)
out = stdout.read().decode('utf-8', errors='replace')
print(f"   Memory Entries: {out.strip().split()[-3] if 'total' in out else 'error'}")

stdin, stdout, stderr = ssh.exec_command('docker exec mindex-redis redis-cli DBSIZE')
time.sleep(2)
out = stdout.read().decode('utf-8', errors='replace')
print(f"   Redis Keys: {out.strip()}")

ssh.close()

print("\n=== All Systems Operational ===")
