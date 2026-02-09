import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = "REDACTED_VM_SSH_PASSWORD"

print("Running ETL test on MINDEX...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=user, password=passwd, timeout=30)

cmd = '''
echo "=== ETL Test Phase 1: Insert test data into memory schema ==="
docker exec mindex-postgres psql -U mycosoft -d mindex << 'SQLEOF'
-- Insert test memory entries
INSERT INTO memory.entries (key, value, scope, namespace, ttl, created_at) VALUES 
('test:etl:001', '{"type": "test", "message": "ETL Pipeline Test 1", "timestamp": "2026-02-04"}', 'system', 'etl_test', NULL, NOW()),
('test:etl:002', '{"type": "test", "message": "ETL Pipeline Test 2", "data": {"count": 100}}', 'system', 'etl_test', NULL, NOW()),
('test:etl:003', '{"type": "test", "message": "ETL Pipeline Test 3", "source": "mindex"}', 'experiment', 'etl_test', NULL, NOW())
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW();

SELECT COUNT(*) as total_entries FROM memory.entries;
SQLEOF

echo ""
echo "=== ETL Test Phase 2: Create Qdrant collection ==="
curl -s -X PUT "http://localhost:6333/collections/mycosoft_knowledge" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 384,
      "distance": "Cosine"
    }
  }' 2>/dev/null

echo ""
echo "=== Qdrant collections ==="
curl -s http://localhost:6333/collections | python3 -m json.tool 2>/dev/null || echo "Qdrant check"

echo ""
echo "=== ETL Test Phase 3: Test ledger block creation ==="
docker exec mindex-postgres psql -U mycosoft -d mindex << 'SQLEOF'
-- Insert a test ledger entry
INSERT INTO ledger.entries (entry_type, data_hash, data, signature) VALUES 
('etl_test', 'abc123hash', '{"test": "ETL ledger entry"}', 'test_sig_001');

SELECT COUNT(*) as ledger_entries FROM ledger.entries;
SQLEOF

echo ""
echo "=== ETL Test Phase 4: Sync to NAS ==="
# Create test file for sync
echo "ETL Test Run: $(date)" > /opt/mycosoft/data/ledger/etl_test.log
echo "Test entries created in MINDEX" >> /opt/mycosoft/data/ledger/etl_test.log

# Run sync
/opt/mycosoft/sync_to_nas.sh

echo ""
echo "=== Verify sync on NAS ==="
sshpass -p 'REDACTED_VM_SSH_PASSWORD' ssh -o StrictHostKeyChecking=no mycosoft@192.168.0.187 "ls -la /mnt/mycosoft-nas/mindex/ledger/"
'''

stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(30)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
