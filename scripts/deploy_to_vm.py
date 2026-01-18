#!/usr/bin/env python3
"""
Deploy Mycosoft Docker images to VM 103
Direct SSH/SCP connection (no Proxmox hop needed)
"""

import paramiko
import os
import sys
import time
from pathlib import Path
from scp import SCPClient

# Configuration
VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"

EXPORT_DIR = Path(r"C:\Users\admin2\Desktop\MYCOSOFT\DOCKER_EXPORTS")

def create_ssh_client():
    """Create SSH client connected to VM"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
    return ssh

def run_cmd(ssh, cmd, sudo=False, show_output=True):
    """Run command on VM"""
    if sudo:
        cmd = f"echo '{VM_PASSWORD}' | sudo -S {cmd}"
    
    if show_output:
        print(f"[VM] {cmd[:80]}...")
    
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=300)
    out = stdout.read().decode()
    err = stderr.read().decode()
    
    if show_output and out:
        print(out[:500])
    if err and "password" not in err.lower():
        print(f"[ERR] {err[:200]}")
    
    return out, err

def check_current_status(ssh):
    """Check current VM status"""
    print("\n" + "="*60)
    print("CURRENT VM STATUS")
    print("="*60)
    
    # Check Docker
    out, _ = run_cmd(ssh, "docker ps --format 'table {{.Names}}\t{{.Status}}'", sudo=True)
    
    # Check disk space
    out, _ = run_cmd(ssh, "df -h /")
    
    # Check /opt/mycosoft
    out, _ = run_cmd(ssh, "ls -la /opt/mycosoft 2>/dev/null || echo 'Directory not found'", sudo=True)

def transfer_images(ssh):
    """Transfer Docker image tar files to VM"""
    print("\n" + "="*60)
    print("TRANSFERRING DOCKER IMAGES")
    print("="*60)
    
    # Create destination directory
    run_cmd(ssh, "mkdir -p /opt/mycosoft/images", sudo=True)
    run_cmd(ssh, "chown -R mycosoft:mycosoft /opt/mycosoft", sudo=True)
    
    # Get list of tar files
    tar_files = list(EXPORT_DIR.glob("*.tar"))
    total_size = sum(f.stat().st_size for f in tar_files)
    print(f"Found {len(tar_files)} images, total size: {total_size / (1024*1024):.1f} MB")
    
    # Create SCP client with progress
    def progress(filename, size, sent):
        pct = (sent / size) * 100
        bar = "=" * int(pct/5) + ">" + " " * (20 - int(pct/5))
        print(f"\r[{bar}] {pct:.1f}% {filename}", end="", flush=True)
    
    scp = SCPClient(ssh.get_transport(), progress=progress)
    
    for tar_file in tar_files:
        size_mb = tar_file.stat().st_size / (1024 * 1024)
        print(f"\nTransferring {tar_file.name} ({size_mb:.1f} MB)...")
        
        try:
            scp.put(str(tar_file), f"/opt/mycosoft/images/{tar_file.name}")
            print(" DONE")
        except Exception as e:
            print(f" FAILED: {e}")
    
    scp.close()
    print("\nAll images transferred!")

def load_images(ssh):
    """Load Docker images from tar files"""
    print("\n" + "="*60)
    print("LOADING DOCKER IMAGES ON VM")
    print("="*60)
    
    # Load each tar file
    run_cmd(ssh, "cd /opt/mycosoft/images && for f in *.tar; do echo Loading $f...; docker load -i $f; done", sudo=True)
    
    # List loaded images
    print("\nLoaded images:")
    run_cmd(ssh, "docker images | grep -E 'mycosoft|mindex|website'", sudo=True)

def pull_third_party_images(ssh):
    """Pull required third-party images"""
    print("\n" + "="*60)
    print("PULLING THIRD-PARTY IMAGES")
    print("="*60)
    
    images = [
        "postgres:17-alpine",
        "postgis/postgis:16-3.4",
        "redis:8-alpine",
        "n8nio/n8n:latest",
        "qdrant/qdrant:v1.13.2",
        "ollama/ollama:latest",
        "fedirz/faster-whisper-server:latest-cpu",
        "rhasspy/wyoming-piper:latest",
        "ghcr.io/matatonic/openedai-speech:latest",
        "nginx:alpine",
        "grafana/grafana:11.6.0",
        "prom/prometheus:v3.2.0",
    ]
    
    for img in images:
        print(f"Pulling {img}...")
        run_cmd(ssh, f"docker pull {img}", sudo=True, show_output=False)
    
    print("All third-party images pulled!")

def create_docker_compose(ssh):
    """Create production docker-compose.yml on VM"""
    print("\n" + "="*60)
    print("CREATING DOCKER-COMPOSE FILE")
    print("="*60)
    
    compose = '''version: "3.8"

services:
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

  mindex-api:
    image: mycosoft-always-on-mindex-api:latest
    container_name: mindex-api
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      MINDEX_DB_HOST: mindex-postgres
      MINDEX_DB_PORT: 5432
      MINDEX_DB_USER: mindex
      MINDEX_DB_PASSWORD: mindex
      MINDEX_DB_NAME: mindex
      API_PREFIX: /api/mindex
      API_KEYS: '["local-dev-key"]'
    depends_on:
      mindex-postgres:
        condition: service_healthy
    networks:
      - mycosoft-network

  mycobrain:
    image: mycosoft-always-on-mycobrain:latest
    container_name: mycobrain
    restart: unless-stopped
    ports:
      - "8003:8003"
    environment:
      MYCOBRAIN_HOST: "0.0.0.0"
      MYCOBRAIN_PORT: "8003"
    networks:
      - mycosoft-network

  mycosoft-website:
    image: website-website:latest
    container_name: mycosoft-website
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      NODE_ENV: production
      MINDEX_API_URL: http://mindex-api:8000
      MYCOBRAIN_SERVICE_URL: http://mycobrain:8003
      MAS_API_URL: http://mas-orchestrator:8000
      N8N_LOCAL_URL: http://n8n:5678
      REDIS_URL: redis://redis:6379
    depends_on:
      - mindex-api
      - mycobrain
    networks:
      - mycosoft-network

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
    
    # Write to file on VM
    sftp = ssh.open_sftp()
    with sftp.file('/opt/mycosoft/docker-compose.yml', 'w') as f:
        f.write(compose)
    sftp.close()
    
    print("docker-compose.yml created!")

def deploy_stack(ssh):
    """Deploy the full stack"""
    print("\n" + "="*60)
    print("DEPLOYING FULL STACK")
    print("="*60)
    
    # Stop existing containers
    print("Stopping existing containers...")
    run_cmd(ssh, "docker stop $(docker ps -aq) 2>/dev/null || true", sudo=True, show_output=False)
    run_cmd(ssh, "docker rm $(docker ps -aq) 2>/dev/null || true", sudo=True, show_output=False)
    
    # Start the stack
    print("Starting services...")
    run_cmd(ssh, "cd /opt/mycosoft && docker compose up -d", sudo=True)
    
    # Wait for services
    print("\nWaiting 30 seconds for services to start...")
    time.sleep(30)
    
    # Check status
    run_cmd(ssh, "docker ps --format 'table {{.Names}}\t{{.Status}}'", sudo=True)

def verify_services(ssh):
    """Verify all services are running"""
    print("\n" + "="*60)
    print("VERIFYING SERVICES")
    print("="*60)
    
    endpoints = [
        ("Website", "http://localhost:3000"),
        ("MINDEX API", "http://localhost:8000/api/mindex/health"),
        ("MycoBrain", "http://localhost:8003/health"),
        ("MAS Orchestrator", "http://localhost:8001/health"),
        ("n8n", "http://localhost:5678"),
        ("MYCA Dashboard", "http://localhost:3100"),
        ("Grafana", "http://localhost:3002"),
    ]
    
    for name, url in endpoints:
        out, _ = run_cmd(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' {url} 2>/dev/null || echo 'FAIL'", sudo=False, show_output=False)
        status = out.strip()
        if status in ['200', '301', '302']:
            print(f"  [OK] {name}: {status}")
        else:
            print(f"  [??] {name}: {status}")

def main():
    print("="*60)
    print("MYCOSOFT FULL DEPLOYMENT TO VM 103")
    print("="*60)
    print(f"Target: {VM_USER}@{VM_IP}")
    print("="*60)
    
    # Connect to VM
    print("\nConnecting to VM...")
    ssh = create_ssh_client()
    print("Connected!")
    
    # Check current status
    check_current_status(ssh)
    
    # Transfer images
    transfer_images(ssh)
    
    # Load images
    load_images(ssh)
    
    # Pull third-party images
    pull_third_party_images(ssh)
    
    # Create docker-compose
    create_docker_compose(ssh)
    
    # Deploy stack
    deploy_stack(ssh)
    
    # Verify
    verify_services(ssh)
    
    ssh.close()
    
    print("\n" + "="*60)
    print("DEPLOYMENT COMPLETE!")
    print("="*60)
    print(f"""
Public URLs (via Cloudflare tunnel):
  - https://sandbox.mycosoft.com (Website)
  - https://api-sandbox.mycosoft.com (MINDEX API)
  - https://brain-sandbox.mycosoft.com (MycoBrain)

Direct Access:
  - http://{VM_IP}:3000 (Website)
  - http://{VM_IP}:5678 (n8n)
  - http://{VM_IP}:3100 (MYCA Dashboard)
  - http://{VM_IP}:3002 (Grafana)
""")

if __name__ == "__main__":
    main()
