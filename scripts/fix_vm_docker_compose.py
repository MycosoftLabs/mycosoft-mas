#!/usr/bin/env python3
"""Fix VM docker-compose to match local always-on setup"""

import paramiko

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"

# The CORRECT docker-compose that matches local always-on setup
DOCKER_COMPOSE = '''version: "3.8"

name: mycosoft-production

services:
  # ----------------------------
  # MINDEX Postgres (PostGIS)
  # ----------------------------
  mindex-postgres:
    image: postgis/postgis:16-3.4
    container_name: mindex-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: mindex
      POSTGRES_USER: mindex
      POSTGRES_PASSWORD: mindex
    volumes:
      - mindex_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mindex -d mindex"]
      interval: 10s
      timeout: 5s
      retries: 10
    networks:
      - mycosoft-network

  # ----------------------------
  # MINDEX API (FastAPI)
  # ----------------------------
  mindex-api:
    image: mycosoft-always-on-mindex-api:latest
    container_name: mindex-api
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      MINDEX_DB_HOST: mindex-postgres
      MINDEX_DB_PORT: "5432"
      MINDEX_DB_USER: mindex
      MINDEX_DB_PASSWORD: mindex
      MINDEX_DB_NAME: mindex
      API_PREFIX: /api/mindex
      API_KEYS: '["local-dev-key"]'
      DEFAULT_PAGE_SIZE: "100"
      MAX_PAGE_SIZE: "1000"
    depends_on:
      mindex-postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/mindex/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 40s
    networks:
      - mycosoft-network

  # ----------------------------
  # MycoBrain (FastAPI)
  # ----------------------------
  mycobrain:
    image: mycosoft-always-on-mycobrain:latest
    container_name: mycobrain
    restart: unless-stopped
    ports:
      - "8003:8003"
    environment:
      MYCOBRAIN_HOST: "0.0.0.0"
      MYCOBRAIN_PORT: "8003"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    networks:
      - mycosoft-network

  # ----------------------------
  # Website (Next.js) - THE REAL MYCOSOFT WEBSITE
  # ----------------------------
  mycosoft-website:
    image: website-website:latest
    container_name: mycosoft-website
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      NODE_ENV: production
      # MINDEX API - Critical for website data
      MINDEX_API_BASE_URL: http://mindex-api:8000
      MINDEX_API_URL: http://mindex-api:8000
      MINDEX_API_KEY: local-dev-key
      # MAS & MycoBrain
      MYCOBRAIN_SERVICE_URL: http://mycobrain:8003
      MAS_API_URL: http://mas-orchestrator:8000
      # n8n
      N8N_LOCAL_URL: http://n8n:5678
      N8N_WEBHOOK_URL: http://n8n:5678
      # Redis
      REDIS_URL: redis://redis:6379
      # NextAuth
      NEXTAUTH_URL: https://sandbox.mycosoft.com
      NEXTAUTH_SECRET: mycosoft-sandbox-secret-key-change-in-production
    depends_on:
      mindex-api:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    networks:
      - mycosoft-network

  # ----------------------------
  # MAS Postgres
  # ----------------------------
  mas-postgres:
    image: postgres:17-alpine
    container_name: mas-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: mas
      POSTGRES_PASSWORD: maspassword
      POSTGRES_DB: mas
    volumes:
      - mas_postgres_data:/var/lib/postgresql/data
    ports:
      - "5433:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mas"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - mycosoft-network

  # ----------------------------
  # Redis
  # ----------------------------
  redis:
    image: redis:8-alpine
    container_name: redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - mycosoft-network

  # ----------------------------
  # Qdrant (Vector DB)
  # ----------------------------
  qdrant:
    image: qdrant/qdrant:v1.13.2
    container_name: qdrant
    restart: unless-stopped
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    networks:
      - mycosoft-network

  # ----------------------------
  # MAS Orchestrator
  # ----------------------------
  mas-orchestrator:
    image: mycosoft-mas-mas-orchestrator:latest
    container_name: mas-orchestrator
    restart: unless-stopped
    ports:
      - "8001:8000"
    environment:
      MAS_ENV: production
      REDIS_URL: redis://redis:6379/0
      DATABASE_URL: postgresql://mas:maspassword@mas-postgres:5432/mas
      QDRANT_URL: http://qdrant:6333
      OLLAMA_URL: http://ollama:11434
      N8N_WEBHOOK_URL: http://n8n:5678
    depends_on:
      redis:
        condition: service_healthy
      mas-postgres:
        condition: service_healthy
    networks:
      - mycosoft-network

  # ----------------------------
  # n8n Workflow Automation
  # ----------------------------
  n8n:
    image: n8nio/n8n:latest
    container_name: n8n
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      N8N_BASIC_AUTH_ACTIVE: "false"
      WEBHOOK_URL: https://n8n.mycosoft.com/
      GENERIC_TIMEZONE: America/New_York
    volumes:
      - n8n_data:/home/node/.n8n
    networks:
      - mycosoft-network

  # ----------------------------
  # Ollama (LLM)
  # ----------------------------
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    restart: unless-stopped
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - mycosoft-network

  # ----------------------------
  # Whisper (Speech-to-Text)
  # ----------------------------
  whisper:
    image: fedirz/faster-whisper-server:latest-cpu
    container_name: whisper
    restart: unless-stopped
    ports:
      - "8765:8000"
    environment:
      WHISPER__MODEL: Systran/faster-whisper-base.en
    volumes:
      - whisper_models:/root/.cache/huggingface
    networks:
      - mycosoft-network

  # ----------------------------
  # Piper TTS
  # ----------------------------
  tts:
    image: rhasspy/wyoming-piper:latest
    container_name: tts
    restart: unless-stopped
    ports:
      - "10200:10200"
    command: --voice en_US-lessac-medium
    volumes:
      - piper_data:/data
    networks:
      - mycosoft-network

  # ----------------------------
  # OpenedAI Speech
  # ----------------------------
  openedai-speech:
    image: ghcr.io/matatonic/openedai-speech:latest
    container_name: openedai-speech
    restart: unless-stopped
    ports:
      - "5500:8000"
    volumes:
      - openedai_data:/data
    networks:
      - mycosoft-network

  # ----------------------------
  # MYCA Dashboard
  # ----------------------------
  myca-dashboard:
    image: mycosoft-mas-unifi-dashboard:latest
    container_name: myca-dashboard
    restart: unless-stopped
    ports:
      - "3100:3000"
    environment:
      NODE_ENV: production
      MAS_BACKEND_URL: http://mas-orchestrator:8000
      N8N_WEBHOOK_URL: http://n8n:5678/webhook/myca/speech
      OPENEDAI_SPEECH_URL: http://openedai-speech:8000/v1/audio/speech
    networks:
      - mycosoft-network

  # ----------------------------
  # Grafana
  # ----------------------------
  grafana:
    image: grafana/grafana:11.6.0
    container_name: grafana
    restart: unless-stopped
    ports:
      - "3002:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - mycosoft-network

  # ----------------------------
  # Prometheus
  # ----------------------------
  prometheus:
    image: prom/prometheus:v3.2.0
    container_name: prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - prometheus_data:/prometheus
    networks:
      - mycosoft-network

networks:
  mycosoft-network:
    driver: bridge

volumes:
  mindex_postgres_data:
  mas_postgres_data:
  redis_data:
  qdrant_data:
  n8n_data:
  ollama_data:
  whisper_models:
  piper_data:
  openedai_data:
  grafana_data:
  prometheus_data:
'''

def run_sudo(ssh, cmd):
    full_cmd = f"echo '{VM_PASSWORD}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=300)
    out = stdout.read().decode()
    err = stderr.read().decode()
    err_clean = "\n".join([l for l in err.split("\n") if "password" not in l.lower() and l.strip()])
    return out, err_clean

def main():
    print("="*60)
    print("FIXING VM DOCKER-COMPOSE")
    print("="*60)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
    print("Connected to VM!")
    
    # Stop all containers
    print("\n1. Stopping all containers...")
    run_sudo(ssh, "docker stop $(docker ps -aq) 2>/dev/null || true")
    run_sudo(ssh, "docker rm $(docker ps -aq) 2>/dev/null || true")
    print("   Done!")
    
    # Write correct docker-compose.yml
    print("\n2. Writing correct docker-compose.yml...")
    sftp = ssh.open_sftp()
    with sftp.file('/opt/mycosoft/docker-compose.yml', 'w') as f:
        f.write(DOCKER_COMPOSE)
    sftp.close()
    print("   Done!")
    
    # Start services
    print("\n3. Starting services with correct config...")
    out, err = run_sudo(ssh, "sh -c 'cd /opt/mycosoft ; docker compose up -d'")
    if err:
        print(f"   Errors: {err[:500]}")
    
    # Wait for services
    print("\n4. Waiting 45 seconds for services to start...")
    import time
    time.sleep(45)
    
    # Check status
    print("\n5. Checking container status...")
    out, _ = run_sudo(ssh, "docker ps --format 'table {{.Names}}\t{{.Status}}'")
    # Filter for ASCII only
    out_clean = ''.join(c for c in out if ord(c) < 128)
    print(out_clean)
    
    # Test endpoints
    print("\n6. Testing endpoints...")
    endpoints = [
        ("Website", "http://localhost:3000"),
        ("MINDEX API health", "http://localhost:8000/api/mindex/health"),
        ("MycoBrain health", "http://localhost:8003/health"),
    ]
    
    for name, url in endpoints:
        stdin, stdout, stderr = ssh.exec_command(f"curl -s -o /dev/null -w '%{{http_code}}' {url} 2>/dev/null")
        code = stdout.read().decode().strip()
        status = "OK" if code in ["200", "301", "302"] else code
        print(f"   {name}: {status}")
    
    ssh.close()
    print("\n" + "="*60)
    print("DONE! Website should now work correctly.")
    print("="*60)

if __name__ == "__main__":
    main()
