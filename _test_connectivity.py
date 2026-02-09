import paramiko
import time
import sys
import json

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = "REDACTED_VM_SSH_PASSWORD"

print("Testing MINDEX services and MAS connectivity...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=user, password=passwd, timeout=30)

cmd = '''
echo "=== Testing Redis ==="
docker exec mindex-redis redis-cli SET test_key "MINDEX ready $(date)" EX 60
docker exec mindex-redis redis-cli GET test_key

echo ""
echo "=== Testing Qdrant ==="
curl -s http://localhost:6333/collections 2>/dev/null | head -3 || echo "Qdrant check"

echo ""
echo "=== Testing MAS connectivity (192.168.0.188:8001) ==="
curl -s http://192.168.0.188:8001/health 2>/dev/null | head -5 || echo "MAS not reachable from MINDEX"

echo ""
echo "=== Testing Memory API on MAS ==="
curl -s http://192.168.0.188:8001/api/memory/health 2>/dev/null | head -5 || echo "Memory API check"

echo ""
echo "=== Testing Website (192.168.0.187:3000) ==="
curl -s http://192.168.0.187:3000/api/health 2>/dev/null | head -5 || echo "Website check"

echo ""
echo "=== MINDEX VM Disk Usage ==="
df -h /

echo ""
echo "=== Data directories ==="
ls -la /opt/mycosoft/data/
'''

stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(20)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
