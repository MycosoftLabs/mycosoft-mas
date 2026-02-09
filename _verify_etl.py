import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = "Mushroom1!Mushroom1!"

print("Verifying ETL results and testing frontend connectivity...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=user, password=passwd, timeout=30)

cmd = '''
echo "=== Memory entries ==="
docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT key, scope, namespace, created_at FROM memory.entries ORDER BY created_at DESC LIMIT 5;"

echo ""
echo "=== Ledger entries ==="
docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT id, entry_type, data_hash, created_at FROM ledger.entries ORDER BY created_at DESC LIMIT 5;"

echo ""
echo "=== Graph nodes (if any) ==="
docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT COUNT(*) as node_count FROM graph.nodes;" 2>/dev/null || echo "No graph data yet"

echo ""
echo "=== Test MAS to MINDEX connectivity ==="
# Call MAS memory API to write to MINDEX
curl -s -X POST "http://192.168.0.188:8001/api/memory/write" \
  -H "Content-Type: application/json" \
  -d '{
    "scope": "system",
    "namespace": "mindex_test",
    "key": "connectivity_test",
    "value": {"from": "mindex_vm", "timestamp": "2026-02-04T22:00:00Z", "status": "connected"}
  }' 2>/dev/null | head -5

echo ""
echo "=== Summary ==="
echo "MINDEX VM: 192.168.0.189"
echo "Database: PostgreSQL (mindex-postgres)"
echo "Cache: Redis (mindex-redis)"  
echo "Vector DB: Qdrant (mindex-qdrant)"
echo "NAS Sync: Configured (hourly)"
echo "Data Path: /opt/mycosoft/data"
'''

stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(20)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
