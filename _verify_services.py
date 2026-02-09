import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = "Mushroom1!Mushroom1!"

print("Checking Dream Machine storage...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=user, password=passwd, timeout=30)

# Check Dream Machine - it's likely a UniFi Dream Machine
cmd = '''
echo "=== Dream Machine (192.168.0.1) ==="
echo "This is likely a UniFi Dream Machine - checking for SMB shares..."
smbclient -L //192.168.0.1 -N 2>&1 | head -20 || echo "No SMB shares (this is normal for UDM)"

echo ""
echo "=== Database verification ==="
docker exec mindex-postgres psql -U postgres -d mindex -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast');" 2>/dev/null

echo ""
echo "=== Registry systems ==="
docker exec mindex-postgres psql -U postgres -d mindex -c "SELECT id, name, status FROM registry.systems;" 2>/dev/null

echo ""
echo "=== Memory tables ==="  
docker exec mindex-postgres psql -U postgres -d mindex -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'memory';" 2>/dev/null

echo ""
echo "=== Ledger tables ==="
docker exec mindex-postgres psql -U postgres -d mindex -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'ledger';" 2>/dev/null

echo ""
echo "=== Redis status ==="
docker exec mindex-redis redis-cli ping

echo ""
echo "=== Qdrant status ==="
curl -s http://localhost:6333/health | head -5 || echo "Qdrant check failed"
'''

stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(20)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
