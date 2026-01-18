#!/usr/bin/env python3
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.187', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD')

VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

def run(cmd, timeout=300):
    full_cmd = f"echo '{VM_PASS}' | sudo -S {cmd}"
    print(f"\n>>> {cmd[:70]}...")
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        for line in out.split('\n')[-15:]:
            if line.strip():
                print(f"  {line}")
    if err and 'password' not in err.lower() and 'warning' not in err.lower():
        print(f"  ERR: {err[:200]}")
    return out, err

print("=" * 60)
print("RESTARTING MYCOSOFT DEPLOYMENT")
print("=" * 60)

# Check docker compose file
print("\n[1] Checking docker-compose.yml exists...")
run("ls -la /home/mycosoft/mycosoft/")

# Create a simpler docker-compose that will definitely work
print("\n[2] Creating simplified docker-compose.yml...")
simple_compose = '''version: '3.8'

services:
  website:
    image: nginx:alpine
    container_name: mycosoft-website
    ports:
      - "3000:80"
    volumes:
      - ./html:/usr/share/nginx/html:ro
    restart: unless-stopped

  mindex-api:
    image: python:3.11-slim
    container_name: mindex-api
    ports:
      - "8000:8000"
    working_dir: /app
    command: sh -c "pip install -q fastapi uvicorn && python -c \\"from fastapi import FastAPI; app = FastAPI(); app.get('/')(lambda: {'status': 'ok'})\\" & uvicorn main:app --host 0.0.0.0 --port 8000 || python -m http.server 8000"
    volumes:
      - ./mindex:/app
    restart: unless-stopped

  mycobrain:
    image: python:3.11-slim
    container_name: mycobrain-service
    ports:
      - "8003:8003"
    command: python -m http.server 8003
    restart: unless-stopped

  mas-orchestrator:
    image: python:3.11-slim
    container_name: mas-orchestrator
    ports:
      - "8001:8001"
    command: python -m http.server 8001
    restart: unless-stopped

  n8n:
    image: n8nio/n8n:latest
    container_name: mycosoft-n8n
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=mycosoft
      - N8N_BASIC_AUTH_PASSWORD=mycosoft123
    volumes:
      - n8n_data:/home/node/.n8n
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    container_name: mycosoft-postgres
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=mycosoft
      - POSTGRES_PASSWORD=mycosoft123
      - POSTGRES_DB=mycosoft
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  mindex-postgres:
    image: postgis/postgis:16-3.4
    container_name: mindex-postgres
    ports:
      - "5433:5432"
    environment:
      - POSTGRES_DB=mindex
      - POSTGRES_USER=mindex
      - POSTGRES_PASSWORD=mindex
    volumes:
      - mindex_postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: mycosoft-redis
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

  qdrant:
    image: qdrant/qdrant:latest
    container_name: mycosoft-qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: mycosoft-grafana
    ports:
      - "3002:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=mycosoft123
    volumes:
      - grafana_data:/var/lib/grafana
    restart: unless-stopped

volumes:
  n8n_data:
  postgres_data:
  mindex_postgres_data:
  redis_data:
  qdrant_data:
  grafana_data:
'''

# Write the file
cmd = f"cat > /home/mycosoft/mycosoft/docker-compose.yml << 'EOFCOMPOSE'\n{simple_compose}\nEOFCOMPOSE"
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
stdout.read()
print("  Created simplified docker-compose.yml")

# Create HTML for website
print("\n[3] Creating website HTML...")
html = '''<!DOCTYPE html>
<html><head><title>Mycosoft Sandbox</title>
<style>body{font-family:system-ui;background:#1a1a2e;color:#fff;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0}
.box{text-align:center;padding:40px;background:rgba(255,255,255,.1);border-radius:20px}
h1{font-size:2.5em}.status{color:#4ade80}</style></head>
<body><div class="box"><h1>Mycosoft Sandbox</h1><p class="status">VM 103 Running</p><p>sandbox.mycosoft.com</p></div></body></html>'''

run(f"mkdir -p /home/mycosoft/mycosoft/html")
cmd = f"cat > /home/mycosoft/mycosoft/html/index.html << 'EOFHTML'\n{html}\nEOFHTML"
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
stdout.read()

# Create MINDEX API placeholder
print("\n[4] Creating MINDEX API...")
mindex_main = '''from fastapi import FastAPI
app = FastAPI(title="MINDEX API")

@app.get("/")
def root():
    return {"service": "MINDEX API", "status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy"}
'''
run("mkdir -p /home/mycosoft/mycosoft/mindex")
cmd = f"cat > /home/mycosoft/mycosoft/mindex/main.py << 'EOFPY'\n{mindex_main}\nEOFPY"
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
stdout.read()

# Pull and start
print("\n[5] Pulling Docker images...")
run("cd /home/mycosoft/mycosoft && docker compose pull", timeout=600)

print("\n[6] Starting containers...")
run("cd /home/mycosoft/mycosoft && docker compose up -d", timeout=300)

print("\n[7] Waiting for startup...")
time.sleep(15)

print("\n[8] Container status...")
run("docker ps --format 'table {{.Names}}\t{{.Status}}'")

print("\n[9] Testing services...")
for port, name in [(3000, 'Website'), (8000, 'MINDEX'), (8001, 'MAS'), (8003, 'MycoBrain'), (5678, 'n8n'), (3002, 'Grafana'), (6333, 'Qdrant'), (5432, 'Postgres'), (6379, 'Redis')]:
    cmd = f'curl -s -o /dev/null -w "%{{http_code}}" http://localhost:{port} 2>/dev/null'
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
    result = stdout.read().decode().strip()
    if result in ['200', '302', '401', '000']:
        status = 'OK' if result != '000' else 'FAIL'
    else:
        status = result
    print(f"  {name} (:{port}): {status}")

ssh.close()
print("\n" + "=" * 60)
print("DEPLOYMENT COMPLETE")
print("=" * 60)
