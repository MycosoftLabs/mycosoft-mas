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

# Check schemas
print("\n=== PostgreSQL Schemas ===")
stdin, stdout, stderr = ssh.exec_command('sudo docker exec mindex-postgres psql -U mycosoft -d mindex -c "\\dn"')
time.sleep(3)
print(stdout.read().decode('utf-8', errors='replace'))

# Check systems
print("\n=== Registered Systems ===")
stdin, stdout, stderr = ssh.exec_command('sudo docker exec mindex-postgres psql -U mycosoft -d mindex -c "SELECT name, type, url FROM registry.systems;"')
time.sleep(3)
print(stdout.read().decode('utf-8', errors='replace'))

# Check Redis
print("\n=== Redis ===")
stdin, stdout, stderr = ssh.exec_command('sudo docker exec mindex-redis redis-cli ping')
time.sleep(2)
print(stdout.read().decode('utf-8', errors='replace'))

# Check Qdrant
print("\n=== Qdrant ===")
stdin, stdout, stderr = ssh.exec_command('curl -s http://localhost:6333/ | head -1')
time.sleep(2)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
print("Database verified!")
