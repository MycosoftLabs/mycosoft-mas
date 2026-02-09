import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
user = "mycosoft"
passwd = "Mushroom1!Mushroom1!"

print("Verifying MINDEX database schemas...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=user, password=passwd, timeout=30)

cmd = '''
# Check schemas
echo "=== Schemas in mindex database ==="
docker exec mindex-postgres psql -U mycosoft -d mindex -c "\\dn"

echo ""
echo "=== Tables in memory schema ==="
docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'memory';" 2>/dev/null

echo ""
echo "=== Registry systems ==="
docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT * FROM registry.systems;" 2>/dev/null || echo "Registry schema needs init"

echo ""
echo "=== Check if init script ran ==="
docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema IN ('memory', 'ledger', 'registry', 'graph');"
'''

stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(10)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
