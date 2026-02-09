import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

mindex_host = "192.168.0.189"
mindex_user = "mycosoft"
mindex_pass = "REDACTED_VM_SSH_PASSWORD"

print("Connecting to MINDEX VM...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(mindex_host, username=mindex_user, password=mindex_pass, timeout=30)
print("Connected!")

# Check PostgreSQL schemas and tables
print("\n=== PostgreSQL Schema Check ===")
cmd = '''sudo docker exec mindex-postgres psql -U mycosoft -d mindex -c "\\dn" 2>&1'''
stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(3)
print(stdout.read().decode('utf-8', errors='replace'))

# Check tables
print("\n=== Tables ===")
cmd = '''sudo docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT schemaname, tablename FROM pg_tables WHERE schemaname IN ('memory', 'ledger', 'registry', 'graph') ORDER BY schemaname, tablename;" 2>&1'''
stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(3)
print(stdout.read().decode('utf-8', errors='replace'))

# Check registered systems
print("\n=== Registered Systems ===")
cmd = '''sudo docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT name, type, url, status FROM registry.systems;" 2>&1'''
stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(3)
print(stdout.read().decode('utf-8', errors='replace'))

# Check Redis
print("\n=== Redis Check ===")
cmd = '''sudo docker exec mindex-redis redis-cli ping 2>&1'''
stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(2)
print(stdout.read().decode('utf-8', errors='replace'))

# Check Qdrant
print("\n=== Qdrant Check ===")
cmd = '''curl -s http://localhost:6333/ 2>&1 | head -5'''
stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(2)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
print("Database verified!")
