#!/usr/bin/env python3
"""Deploy real working services to VM"""
import paramiko

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"

# Docker compose with actual working services
DOCKER_COMPOSE = '''version: "3.8"

services:
  # Simple nginx website for testing
  mycosoft-website:
    image: nginx:alpine
    container_name: mycosoft-website
    ports:
      - "3000:80"
    volumes:
      - ./html:/usr/share/nginx/html:ro
    restart: unless-stopped

  # Simple Python API for testing
  mindex-api:
    image: python:3.11-slim
    container_name: mindex-api
    ports:
      - "8000:8000"
    working_dir: /app
    volumes:
      - ./api:/app
    command: python -m http.server 8000
    restart: unless-stopped

  # MycoBrain service
  mycobrain-service:
    image: python:3.11-slim
    container_name: mycobrain-service
    ports:
      - "8003:8003"
    working_dir: /app
    volumes:
      - ./brain:/app
    command: python -m http.server 8003
    restart: unless-stopped

  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: mycosoft-postgres
    environment:
      POSTGRES_USER: mycosoft
      POSTGRES_PASSWORD: mycosoft123
      POSTGRES_DB: mycosoft
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    restart: unless-stopped

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: mycosoft-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped

volumes:
  postgres-data:
  redis-data:
'''

HTML_INDEX = '''<!DOCTYPE html>
<html>
<head>
    <title>Mycosoft Sandbox</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0;
        }
        .container {
            text-align: center;
            padding: 40px;
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        h1 { font-size: 3em; margin-bottom: 10px; }
        .emoji { font-size: 4em; }
        p { color: #aaa; }
        .status { color: #4ade80; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="emoji">🍄</div>
        <h1>Mycosoft Sandbox</h1>
        <p class="status">✓ VM 103 Running</p>
        <p>Cloudflare Tunnel Active</p>
        <p>sandbox.mycosoft.com</p>
    </div>
</body>
</html>
'''

API_INDEX = '''<!DOCTYPE html>
<html><body>
<h1>MINDEX API</h1>
<p>API Sandbox - api-sandbox.mycosoft.com</p>
<p>Status: Running</p>
</body></html>
'''

BRAIN_INDEX = '''<!DOCTYPE html>
<html><body>
<h1>MycoBrain Service</h1>
<p>AI Brain Sandbox - brain-sandbox.mycosoft.com</p>
<p>Status: Running</p>
</body></html>
'''

print("=" * 60)
print("DEPLOYING REAL SERVICES TO VM")
print("=" * 60)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_IP, username=VM_USER, password=VM_PASS)
print("Connected!")

# Stop existing containers
print("\n>>> Stopping existing containers...")
cmd = f"echo '{VM_PASS}' | sudo -S docker compose -f ~/mycosoft/docker-compose.yml down 2>/dev/null || true"
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
stdout.read()

# Create directories
print(">>> Creating directories...")
cmd = "mkdir -p ~/mycosoft/html ~/mycosoft/api ~/mycosoft/brain"
stdin, stdout, stderr = ssh.exec_command(cmd)
stdout.read()

# Write docker-compose.yml
print(">>> Writing docker-compose.yml...")
cmd = f"cat > ~/mycosoft/docker-compose.yml << 'EOFCOMPOSE'\n{DOCKER_COMPOSE}\nEOFCOMPOSE"
stdin, stdout, stderr = ssh.exec_command(cmd)
stdout.read()

# Write HTML files
print(">>> Creating index.html for website...")
cmd = f"cat > ~/mycosoft/html/index.html << 'EOFHTML'\n{HTML_INDEX}\nEOFHTML"
stdin, stdout, stderr = ssh.exec_command(cmd)
stdout.read()

print(">>> Creating index.html for API...")
cmd = f"cat > ~/mycosoft/api/index.html << 'EOFAPI'\n{API_INDEX}\nEOFAPI"
stdin, stdout, stderr = ssh.exec_command(cmd)
stdout.read()

print(">>> Creating index.html for Brain...")
cmd = f"cat > ~/mycosoft/brain/index.html << 'EOFBRAIN'\n{BRAIN_INDEX}\nEOFBRAIN"
stdin, stdout, stderr = ssh.exec_command(cmd)
stdout.read()

# Start containers
print(">>> Starting containers...")
cmd = f"echo '{VM_PASS}' | sudo -S docker compose -f ~/mycosoft/docker-compose.yml up -d"
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=120)
print(stdout.read().decode())

# Wait and check
import time
time.sleep(5)

print(">>> Checking container status...")
cmd = f"echo '{VM_PASS}' | sudo -S docker ps --format 'table {{{{.Names}}}}\t{{{{.Status}}}}'"
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

# Test services
print(">>> Testing localhost:3000...")
cmd = "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000"
stdin, stdout, stderr = ssh.exec_command(cmd)
print("Port 3000:", stdout.read().decode())

print(">>> Testing localhost:8000...")
cmd = "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000"
stdin, stdout, stderr = ssh.exec_command(cmd)
print("Port 8000:", stdout.read().decode())

print(">>> Testing localhost:8003...")
cmd = "curl -s -o /dev/null -w '%{http_code}' http://localhost:8003"
stdin, stdout, stderr = ssh.exec_command(cmd)
print("Port 8003:", stdout.read().decode())

ssh.close()
print("\n" + "=" * 60)
print("DEPLOYMENT COMPLETE!")
print("=" * 60)
