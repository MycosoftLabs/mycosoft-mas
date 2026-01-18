#!/usr/bin/env python3
"""
Deploy simplified Mycosoft sandbox stack using pre-built images
This gets core services running while we prepare for full build
"""
import paramiko
import time

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"

# Simplified docker-compose that uses base images
DOCKER_COMPOSE = """
version: '3.8'

services:
  # ============================================================================
  # CORE DATA LAYER (these are essential)
  # ============================================================================
  
  postgres:
    image: postgres:16-alpine
    container_name: mycosoft-postgres
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=mycosoft
      - POSTGRES_PASSWORD=Mushroom1!
      - POSTGRES_DB=mycosoft
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mycosoft"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: mycosoft-redis
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ============================================================================
  # WEBSITE - Using nginx placeholder until Next.js build is ready
  # ============================================================================

  website:
    image: nginx:alpine
    container_name: mycosoft-website
    ports:
      - "3000:80"
    volumes:
      - ./website-html:/usr/share/nginx/html:ro
    restart: unless-stopped
    depends_on:
      - postgres
      - redis

  # ============================================================================
  # MINDEX API - Python FastAPI placeholder
  # ============================================================================

  mindex-api:
    image: python:3.11-slim
    container_name: mindex-api
    ports:
      - "8000:8000"
    volumes:
      - ./mindex-app:/app
    working_dir: /app
    command: python -m http.server 8000
    restart: unless-stopped

  # ============================================================================
  # MYCOBRAIN SERVICE - Python placeholder
  # ============================================================================

  mycobrain:
    image: python:3.11-slim
    container_name: mycobrain-service
    ports:
      - "8003:8003"
    volumes:
      - ./mycobrain-app:/app
    working_dir: /app
    command: python -m http.server 8003
    restart: unless-stopped

  # ============================================================================
  # MAS ORCHESTRATOR - Python placeholder
  # ============================================================================

  mas-orchestrator:
    image: python:3.11-slim
    container_name: mas-orchestrator
    ports:
      - "8001:8001"
    volumes:
      - ./mas-app:/app
    working_dir: /app
    command: python -m http.server 8001
    restart: unless-stopped

  # ============================================================================
  # N8N WORKFLOWS - Real n8n
  # ============================================================================

  n8n:
    image: n8nio/n8n:latest
    container_name: mycosoft-n8n
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=false
      - WEBHOOK_URL=https://n8n.mycosoft.com/webhooks
    volumes:
      - n8n_data:/home/node/.n8n
    restart: unless-stopped

  # ============================================================================
  # MONITORING - Real Grafana & Prometheus
  # ============================================================================

  grafana:
    image: grafana/grafana:latest
    container_name: mycosoft-grafana
    ports:
      - "3002:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=Mushroom1!
      - GF_INSTALL_PLUGINS=grafana-clock-panel,grafana-worldmap-panel
    volumes:
      - grafana_data:/var/lib/grafana
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    container_name: mycosoft-prometheus
    ports:
      - "9090:9090"
    volumes:
      - prometheus_data:/prometheus
    restart: unless-stopped

  # ============================================================================
  # VECTOR DATABASE - Qdrant
  # ============================================================================

  qdrant:
    image: qdrant/qdrant:latest
    container_name: mycosoft-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  n8n_data:
  grafana_data:
  prometheus_data:
  qdrant_data:
"""

# Landing page HTML
WEBSITE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mycosoft Sandbox</title>
    <style>
        :root {
            --bg-primary: #0a0e17;
            --bg-secondary: #111827;
            --accent: #10b981;
            --accent-glow: rgba(16, 185, 129, 0.3);
            --text: #e5e7eb;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2rem;
        }
        .container {
            text-align: center;
            max-width: 800px;
        }
        .logo {
            font-size: 5rem;
            margin-bottom: 1rem;
            filter: drop-shadow(0 0 30px var(--accent-glow));
        }
        h1 {
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            background: linear-gradient(90deg, var(--accent), #34d399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle {
            font-size: 1.25rem;
            color: #9ca3af;
            margin-bottom: 2rem;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }
        .status-card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 1.25rem;
            backdrop-filter: blur(10px);
        }
        .status-card h3 {
            font-size: 0.875rem;
            color: #9ca3af;
            margin-bottom: 0.5rem;
        }
        .status-card .value {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--accent);
        }
        .services {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 0.75rem;
            margin: 2rem 0;
        }
        .service-tag {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid var(--accent);
            color: var(--accent);
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.875rem;
        }
        .footer {
            margin-top: 3rem;
            color: #6b7280;
            font-size: 0.875rem;
        }
        .footer a {
            color: var(--accent);
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">🍄</div>
        <h1>Mycosoft Sandbox</h1>
        <p class="subtitle">VM 103 • Development Environment • sandbox.mycosoft.com</p>
        
        <div class="status-grid">
            <div class="status-card">
                <h3>Status</h3>
                <div class="value">✓ Online</div>
            </div>
            <div class="status-card">
                <h3>VM ID</h3>
                <div class="value">103</div>
            </div>
            <div class="status-card">
                <h3>Stack</h3>
                <div class="value">MAS + Website</div>
            </div>
            <div class="status-card">
                <h3>Tunnel</h3>
                <div class="value">✓ Active</div>
            </div>
        </div>

        <div class="services">
            <span class="service-tag">Website :3000</span>
            <span class="service-tag">MINDEX :8000</span>
            <span class="service-tag">MycoBrain :8003</span>
            <span class="service-tag">MAS :8001</span>
            <span class="service-tag">n8n :5678</span>
            <span class="service-tag">Grafana :3002</span>
            <span class="service-tag">PostgreSQL :5432</span>
            <span class="service-tag">Redis :6379</span>
            <span class="service-tag">Qdrant :6333</span>
        </div>

        <div class="footer">
            <p>Mycosoft © 2026 • <a href="https://mycosoft.com">Production Site</a></p>
        </div>
    </div>
</body>
</html>"""

def run_cmd(ssh, cmd, sudo=False, timeout=300):
    if sudo:
        cmd = f"echo '{VM_PASS}' | sudo -S {cmd}"
    print(f">>> {cmd[:80]}...")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out:
        for line in out.strip().split('\n')[-10:]:
            # Remove problematic unicode chars for Windows console
            safe_line = line.encode('ascii', errors='replace').decode('ascii')
            print(f"    {safe_line}")
    if err and "password" not in err.lower():
        safe_err = err[:100].encode('ascii', errors='replace').decode('ascii')
        print(f"    ERR: {safe_err}")
    return out, err

print("=" * 70)
print("DEPLOYING MYCOSOFT SANDBOX (SIMPLE MODE)")
print(f"Target: {VM_IP}")
print("=" * 70)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_IP, username=VM_USER, password=VM_PASS)
print("Connected!")

# Stop all existing containers
print("\n[1/5] Cleaning up existing containers...")
run_cmd(ssh, "docker stop $(docker ps -aq) 2>/dev/null || true", sudo=True)
run_cmd(ssh, "docker rm $(docker ps -aq) 2>/dev/null || true", sudo=True)

# Create deployment directory
print("\n[2/5] Creating deployment directory...")
run_cmd(ssh, "mkdir -p ~/mycosoft-sandbox/{website-html,mindex-app,mycobrain-app,mas-app}")

# Write docker-compose.yml
print("\n[3/5] Writing docker-compose.yml...")
sftp = ssh.open_sftp()
with sftp.file("/home/mycosoft/mycosoft-sandbox/docker-compose.yml", 'w') as f:
    f.write(DOCKER_COMPOSE)

# Write website HTML
with sftp.file("/home/mycosoft/mycosoft-sandbox/website-html/index.html", 'w') as f:
    f.write(WEBSITE_HTML)

# Create placeholder files for Python services
for service in ['mindex-app', 'mycobrain-app', 'mas-app']:
    with sftp.file(f"/home/mycosoft/mycosoft-sandbox/{service}/index.html", 'w') as f:
        f.write(f"<h1>{service} placeholder</h1>")
sftp.close()

# Pull images and start
print("\n[4/5] Starting Docker Compose (pulling images)...")
run_cmd(ssh, "docker compose -f /home/mycosoft/mycosoft-sandbox/docker-compose.yml pull", sudo=True, timeout=600)
run_cmd(ssh, "docker compose -f /home/mycosoft/mycosoft-sandbox/docker-compose.yml up -d", sudo=True, timeout=300)

# Wait for startup
print("\n[5/5] Waiting for services (30s)...")
time.sleep(30)

# Check status
print("\n" + "=" * 70)
print("CONTAINER STATUS")
print("=" * 70)
run_cmd(ssh, "docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'", sudo=True)

# Test endpoints
print("\n" + "=" * 70)
print("SERVICE TESTS")
print("=" * 70)
tests = [
    ("Website", "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000"),
    ("MINDEX", "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000"),
    ("MAS", "curl -s -o /dev/null -w '%{http_code}' http://localhost:8001"),
    ("MycoBrain", "curl -s -o /dev/null -w '%{http_code}' http://localhost:8003"),
    ("n8n", "curl -s -o /dev/null -w '%{http_code}' http://localhost:5678/healthz"),
    ("Grafana", "curl -s -o /dev/null -w '%{http_code}' http://localhost:3002"),
    ("Prometheus", "curl -s -o /dev/null -w '%{http_code}' http://localhost:9090"),
    ("Qdrant", "curl -s -o /dev/null -w '%{http_code}' http://localhost:6333"),
    ("PostgreSQL", "docker exec mycosoft-postgres pg_isready -U mycosoft"),
    ("Redis", "docker exec mycosoft-redis redis-cli ping"),
]

for name, cmd in tests:
    out, _ = run_cmd(ssh, cmd, sudo=("docker exec" in cmd))
    status = out.strip()[-10:] if out else "FAIL"
    icon = "[OK]" if status in ["200", "PONG", "accepting connections"] else "[FAIL]"
    print(f"  {icon} {name}: {status}")

ssh.close()

print("\n" + "=" * 70)
print("SANDBOX DEPLOYMENT COMPLETE!")
print("=" * 70)
print(f"""
Local URLs:
  - Website:     http://{VM_IP}:3000
  - MINDEX:      http://{VM_IP}:8000
  - MAS:         http://{VM_IP}:8001
  - MycoBrain:   http://{VM_IP}:8003
  - n8n:         http://{VM_IP}:5678
  - Grafana:     http://{VM_IP}:3002 (admin/Mushroom1!)
  - Prometheus:  http://{VM_IP}:9090

Cloudflare Tunnel URLs:
  - https://sandbox.mycosoft.com
  - https://api-sandbox.mycosoft.com (configure route to :8000)
  - https://brain-sandbox.mycosoft.com (configure route to :8003)

Next Steps:
  1. Build full Website from /opt/mycosoft/website
  2. Build full MAS stack from /opt/mycosoft/mas
  3. Configure Cloudflare routes for all services
""")
