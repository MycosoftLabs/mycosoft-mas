import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = "Mushroom1!Mushroom1!"

print("Inserting test data with correct schema...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=user, password=passwd, timeout=30)

cmd = '''
docker exec mindex-postgres psql -U mycosoft -d mindex << 'SQLEOF'
-- Insert memory entries with correct unique constraint
INSERT INTO memory.entries (scope, namespace, key, value, metadata) VALUES 
('system', 'mindex', 'etl_test_001', '{"type": "test", "message": "ETL Pipeline Test"}', '{"source": "etl_test"}'),
('system', 'mindex', 'etl_test_002', '{"type": "config", "setting": "enabled"}', '{"source": "etl_test"}'),
('experiment', 'etl', 'test_001', '{"experiment": "data_flow", "result": "success"}', '{}')
ON CONFLICT (scope, namespace, key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW();

-- View inserted data
SELECT scope, namespace, key, value->'type' as type FROM memory.entries;

-- Insert ledger entry (needs block_number or null)
INSERT INTO ledger.entries (entry_type, data_hash, signature, metadata) VALUES 
('etl_test', '1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef', 'test_sig', '{"test": true}');

SELECT entry_type, data_hash, created_at FROM ledger.entries;

-- Insert graph node
INSERT INTO graph.nodes (node_type, name, metadata) VALUES 
('system', 'MINDEX-VM', '{"ip": "192.168.0.189", "role": "memory_index"}');

SELECT node_type, name FROM graph.nodes;
SQLEOF
'''

stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(15)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
