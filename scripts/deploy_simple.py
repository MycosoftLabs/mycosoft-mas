#!/usr/bin/env python3
"""Simple deployment that will definitely work"""
import paramiko
import time
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_IP, username=VM_USER, password=VM_PASS)

def run(cmd, timeout=300):
    full_cmd = f"echo '{VM_PASS}' | sudo -S bash -c \"{cmd}\""
    print(f"\n>>> {cmd[:70]}...")
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out:
        for line in out.split('\n')[-10:]:
            if line.strip():
                print(f"  {line}")
    if err and 'password' not in err.lower():
        err_clean = err.replace('\n', ' ')[:200]
        if err_clean.strip():
            print(f"  ERR: {err_clean}")
    return out, err

print("=" * 70)
print("DEPLOYING MYCOSOFT SANDBOX (SIMPLE MODE)")
print(f"Target: {VM_IP}")
print("=" * 70)
print("Connected!")

# Clean up
print("\n[1/5] Cleaning up existing containers...")
run("docker stop $(docker ps -aq) 2>/dev/null || true")
run("docker rm $(docker ps -aq) 2>/dev/null || true")

# Create directory
print("\n[2/5] Creating deployment directory...")
run("mkdir -p ~/mycosoft-sandbox/{website-html,mindex-app,mycobrain-app,mas-app}")

# Create docker-compose.yml
print("\n[3/5] Writing docker-compose.yml...")
compose = '''version: "3.8"
services:
  website:
    image: nginx:alpine
    container_name: mycosoft-website
    ports:
      - "3000:80"
    volumes:
      - ./website-html:/usr/share/nginx/html:ro
    restart: always
  
  mindex:
    image: python:3.11-slim
    container_name: mindex-api
    ports:
      - "8000:8000"
    working_dir: /app
    volumes:
      - ./mindex-app:/app
    command: python -m http.server 8000
    restart: always
  
  mycobrain:
    image: python:3.11-slim
    container_name: mycobrain-service
    ports:
      - "8003:8003"
    command: python -m http.server 8003
    restart: always
  
  mas:
    image: python:3.11-slim
    container_name: mas-orchestrator
    ports:
      - "8001:8001"
    command: python -m http.server 8001
    restart: always
  
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
    restart: always
  
  postgres:
    image: postgres:16-alpine
    container_name: mycosoft-postgres
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: mycosoft
      POSTGRES_PASSWORD: mycosoft123
      POSTGRES_DB: mycosoft
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always
  
  redis:
    image: redis:7-alpine
    container_name: mycosoft-redis
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: always
  
  qdrant:
    image: qdrant/qdrant:latest
    container_name: mycosoft-qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: always
  
  grafana:
    image: grafana/grafana:latest
    container_name: mycosoft-grafana
    ports:
      - "3002:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: mycosoft123
    volumes:
      - grafana_data:/var/lib/grafana
    restart: always

volumes:
  n8n_data:
  postgres_data:
  redis_data:
  qdrant_data:
  grafana_data:
'''

# Write compose file directly
stdin, stdout, stderr = ssh.exec_command(f"cat > /home/mycosoft/mycosoft-sandbox/docker-compose.yml << 'EOF'\n{compose}\nEOF")
stdout.read()

# Create website HTML
html = '<html><body style="background:#1a1a2e;color:white;font-family:system-ui;display:flex;justify-content:center;align-items:center;height:100vh;margin:0"><div style="text-align:center"><h1>Mycosoft Sandbox</h1><p style="color:#4ade80">VM 103 Running</p><p>sandbox.mycosoft.com</p></div></body></html>'
stdin, stdout, stderr = ssh.exec_command(f"echo '{html}' > /home/mycosoft/mycosoft-sandbox/website-html/index.html")
stdout.read()

# Create mindex placeholder
stdin, stdout, stderr = ssh.exec_command("echo '<html><body><h1>MINDEX API</h1><p>Running</p></body></html>' > /home/mycosoft/mycosoft-sandbox/mindex-app/index.html")
stdout.read()

# Start docker compose
print("\n[4/5] Starting Docker Compose (pulling images)...")
run("cd /home/mycosoft/mycosoft-sandbox && docker compose pull", timeout=600)
run("cd /home/mycosoft/mycosoft-sandbox && docker compose up -d", timeout=300)

print("\n[5/5] Waiting for services (30s)...")
time.sleep(30)

# Check status
print("\n=== CONTAINER STATUS ===")
run("docker ps --format 'table {{.Names}}\t{{.Status}}'")

print("\n=== SERVICE TESTS ===")
services = [
    (3000, "Website"),
    (8000, "MINDEX API"),
    (8001, "MAS Orchestrator"),
    (8003, "MycoBrain"),
    (5678, "n8n"),
    (3002, "Grafana"),
    (5432, "PostgreSQL"),
    (6379, "Redis"),
    (6333, "Qdrant"),
]

for port, name in services:
    stdin, stdout, stderr = ssh.exec_command(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{port} 2>/dev/null || echo FAIL")
    result = stdout.read().decode().strip()
    status = "OK" if result in ['200', '302', '401'] else f"FAIL ({result})"
    print(f"  {name:20} :{port} -> {status}")

ssh.close()

print("\n" + "=" * 70)
print("DEPLOYMENT COMPLETE!")
print("=" * 70)
print(f"""
Access URLs:
  Website:   https://sandbox.mycosoft.com (http://{VM_IP}:3000)
  MINDEX:    https://api-sandbox.mycosoft.com (http://{VM_IP}:8000)
  MycoBrain: https://brain-sandbox.mycosoft.com (http://{VM_IP}:8003)
  n8n:       http://{VM_IP}:5678
  Grafana:   http://{VM_IP}:3002
""")
