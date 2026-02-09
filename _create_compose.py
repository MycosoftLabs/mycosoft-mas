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

# Create docker-compose file
print("\n=== Creating docker-compose.yml ===")
docker_compose = '''version: "3.9"

services:
  postgres:
    image: postgres:15-alpine
    container_name: mindex-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: mycosoft
      POSTGRES_PASSWORD: REDACTED_DB_PASSWORD
      POSTGRES_DB: mindex
    volumes:
      - /data/postgres:/var/lib/postgresql/data
      - ./init-postgres.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    ports:
      - "5432:5432"
    networks:
      - mindex-network

  redis:
    image: redis:7-alpine
    container_name: mindex-redis
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 1gb --maxmemory-policy allkeys-lru
    volumes:
      - /data/redis:/data
    ports:
      - "6379:6379"
    networks:
      - mindex-network

  qdrant:
    image: qdrant/qdrant:latest
    container_name: mindex-qdrant
    restart: unless-stopped
    volumes:
      - /data/qdrant:/qdrant/storage
    ports:
      - "6333:6333"
      - "6334:6334"
    networks:
      - mindex-network

networks:
  mindex-network:
    driver: bridge
'''

# Write compose file
cmd = f'''cat > /opt/mycosoft/mindex/docker-compose.yml << 'EOF'
{docker_compose}
EOF
cat /opt/mycosoft/mindex/docker-compose.yml
'''
stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(3)
print(stdout.read().decode('utf-8', errors='replace'))

# Create data directories
print("\n=== Creating data directories ===")
stdin, stdout, stderr = ssh.exec_command("sudo mkdir -p /data/postgres /data/redis /data/qdrant && sudo chown -R 999:999 /data/postgres && ls -la /data/")
time.sleep(2)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
print("Docker compose file created!")
