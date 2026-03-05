"""Write clean compose file to VM 191 and start the stack."""
import os
import time
import paramiko

key_path = os.path.expanduser("~/.ssh/myca_vm191")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pkey = paramiko.Ed25519Key.from_private_key_file(key_path)
ssh.connect("192.168.0.191", username="mycosoft", pkey=pkey, timeout=15)

VM_PASSWORD = ""
creds_file = os.path.join(os.path.dirname(__file__), "../.credentials.local")
if os.path.exists(creds_file):
    for line in open(creds_file).read().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() in ("VM_PASSWORD", "VM_SSH_PASSWORD"):
                VM_PASSWORD = v.strip()

def run(cmd, timeout=120):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode("utf-8", errors="replace").strip()

def sudo(cmd, timeout=120):
    return run(f"echo {VM_PASSWORD} | sudo -S {cmd}", timeout=timeout)

# Write compose file via heredoc on the VM itself
compose_content = """version: "3.9"

services:
  myca-workspace-api:
    image: python:3.11-slim
    container_name: myca-workspace-api
    restart: unless-stopped
    working_dir: /app
    volumes:
      - /opt/myca/workspace-api:/app
      - /opt/myca/credentials:/opt/myca/credentials:ro
      - /opt/myca/data:/opt/myca/data
      - /opt/myca/logs:/opt/myca/logs
    env_file: /opt/myca/.env
    environment:
      - PYTHONPATH=/app
    command: >
      bash -c "pip install -q fastapi uvicorn httpx asyncpg redis aiofiles
      python-multipart pydantic google-auth google-api-python-client
      && uvicorn workspace_api:app --host 0.0.0.0 --port 8100 --reload"
    ports:
      - "8100:8100"
    networks:
      - myca-net
    depends_on:
      - myca-postgres
      - myca-redis

  myca-n8n:
    image: n8nio/n8n:latest
    container_name: myca-n8n
    restart: unless-stopped
    env_file: /opt/myca/.env
    environment:
      - N8N_HOST=0.0.0.0
      - N8N_PORT=5679
      - N8N_PROTOCOL=http
      - WEBHOOK_URL=http://192.168.0.191:5679
      - N8N_BASIC_AUTH_ACTIVE=true
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=myca-postgres
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=myca_n8n
      - DB_POSTGRESDB_USER=myca
      - EXECUTIONS_DATA_SAVE_ON_SUCCESS=all
      - GENERIC_TIMEZONE=America/Los_Angeles
    ports:
      - "5679:5679"
    volumes:
      - myca-n8n-data:/home/node/.n8n
    networks:
      - myca-net
    depends_on:
      - myca-postgres

  myca-postgres:
    image: postgres:15-alpine
    container_name: myca-postgres
    restart: unless-stopped
    env_file: /opt/myca/.env
    environment:
      - POSTGRES_USER=myca
      - POSTGRES_DB=myca_workspace
    volumes:
      - myca-postgres-data:/var/lib/postgresql/data
    ports:
      - "5433:5432"
    networks:
      - myca-net

  myca-redis:
    image: redis:7-alpine
    container_name: myca-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - myca-redis-data:/data
    ports:
      - "6380:6379"
    networks:
      - myca-net

volumes:
  myca-postgres-data:
  myca-redis-data:
  myca-n8n-data:

networks:
  myca-net:
    driver: bridge
"""

# Write via SFTP with explicit ASCII encoding
sftp = ssh.open_sftp()
with sftp.open("/opt/myca/docker-compose.yml", "w") as f:
    f.write(compose_content.encode("ascii").decode("ascii"))
sftp.close()
print("Compose file written (clean ASCII)")

# Validate
out = run("cat /opt/myca/docker-compose.yml | head -5")
print("First 5 lines:", out)

# Start the stack
print("\nStarting Docker stack (pulling images on first run)...")
out = sudo("docker compose -f /opt/myca/docker-compose.yml up -d 2>&1", timeout=300)
print("Output:", out[-600:])

time.sleep(30)

# Verify
print("\nVerification:")
out = sudo("docker ps --format '{{.Names}}  {{.Status}}'")
print("Containers:")
for line in out.split("\n"):
    if line.strip():
        print(f"  {line.strip()}")

out = run("curl -s http://localhost:8100/health 2>/dev/null || echo 'starting...'")
print(f"Workspace API: {out[:200]}")

out = run("curl -s -o /dev/null -w '%{http_code}' http://localhost:5679/ 2>/dev/null || echo 'starting...'")
print(f"n8n status code: {out}")

ssh.close()
print("\nDone! VM 191 MYCA workspace is live.")
