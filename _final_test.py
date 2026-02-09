import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = "REDACTED_VM_SSH_PASSWORD"

print("Complete MINDEX ETL and Integration Test...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=user, password=passwd, timeout=30)

# Add more test data and run final verification
cmds = [
    # Insert more memory entries
    '''docker exec mindex-postgres psql -U mycosoft -d mindex -c "INSERT INTO memory.entries (scope, namespace, key, value, metadata) VALUES ('system', 'mindex', 'config', '{\\\"version\\\": \\\"1.0\\\", \\\"initialized\\\": true}', '{\\\"type\\\": \\\"config\\\"}') ON CONFLICT (scope, namespace, key) DO NOTHING;"''',
    '''docker exec mindex-postgres psql -U mycosoft -d mindex -c "INSERT INTO memory.entries (scope, namespace, key, value) VALUES ('agent', 'myca', 'state', '{\\\"active\\\": true, \\\"mode\\\": \\\"autonomous\\\"}') ON CONFLICT (scope, namespace, key) DO NOTHING;"''',
    
    # Insert ledger entry
    '''docker exec mindex-postgres psql -U mycosoft -d mindex -c "INSERT INTO ledger.entries (entry_type, data_hash, signature) VALUES ('system_init', 'abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234', 'sig_001');"''',
    
    # Insert graph node
    '''docker exec mindex-postgres psql -U mycosoft -d mindex -c "INSERT INTO graph.nodes (node_type, name, metadata) VALUES ('service', 'mindex-postgres', '{\\\"port\\\": 5432}') ON CONFLICT DO NOTHING;"''',
    '''docker exec mindex-postgres psql -U mycosoft -d mindex -c "INSERT INTO graph.nodes (node_type, name, metadata) VALUES ('service', 'mindex-redis', '{\\\"port\\\": 6379}') ON CONFLICT DO NOTHING;"''',
    
    # Final counts
    '''echo "=== Final Counts ===" && docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT 'memory' as schema, COUNT(*) FROM memory.entries UNION ALL SELECT 'ledger', COUNT(*) FROM ledger.entries UNION ALL SELECT 'graph', COUNT(*) FROM graph.nodes UNION ALL SELECT 'registry', COUNT(*) FROM registry.systems;"''',
    
    # Sync to NAS
    '''/opt/mycosoft/sync_to_nas.sh''',
    
    # Final status
    '''echo "=== Final NAS Contents ===" && sshpass -p 'REDACTED_VM_SSH_PASSWORD' ssh -o StrictHostKeyChecking=no mycosoft@192.168.0.187 "ls -la /mnt/mycosoft-nas/mindex/"''',
]

for cmd in cmds:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    time.sleep(3)
    out = stdout.read().decode('utf-8', errors='replace')
    if out.strip():
        print(out)

ssh.close()
print("\n=== Test Complete ===")
