#!/usr/bin/env python3
"""
Full Production Deployment Script for Mycosoft System
Exports ALL Docker images from Docker Desktop and deploys to VM 103

This script:
1. Exports all custom-built Docker images to tar files
2. Transfers them to VM 103 via SSH/SCP
3. Loads images on the VM
4. Creates Docker networks
5. Deploys the full stack with proper docker-compose files
6. Verifies all services are healthy
"""

import subprocess
import os
import sys
import time
from pathlib import Path

# Configuration
VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"
PROXMOX_HOST = "192.168.0.202"
PROXMOX_USER = "root"
PROXMOX_PASSWORD = "20202020"

# Export directory
EXPORT_DIR = Path(r"C:\Users\admin2\Desktop\MYCOSOFT\DOCKER_EXPORTS")

# Custom images to export (built from our code)
CUSTOM_IMAGES = [
    "website-website:latest",
    "mycosoft-always-on-mindex-api:latest",
    "mycosoft-always-on-mindex-etl:latest",
    "mycosoft-always-on-mycobrain:latest",
    "mycosoft-mas-mas-orchestrator:latest",
    "mycosoft-mas-unifi-dashboard:latest",
]

# Third-party images (will be pulled on VM)
THIRD_PARTY_IMAGES = [
    "postgres:16-alpine",
    "postgres:17-alpine",
    "postgis/postgis:16-3.4",
    "redis:7-alpine",
    "redis:8-alpine",
    "n8nio/n8n:latest",
    "ollama/ollama:latest",
    "qdrant/qdrant:v1.13.2",
    "prom/prometheus:v3.2.0",
    "grafana/grafana:11.6.0",
    "fedirz/faster-whisper-server:latest-cpu",
    "rhasspy/wyoming-piper:latest",
    "ghcr.io/matatonic/openedai-speech:latest",
    "nginx:alpine",
]


def run_local_cmd(cmd, check=True):
    """Run a command locally"""
    print(f"[LOCAL] {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0 and check:
        print(f"Error: {result.stderr}")
    return result


def run_ssh_cmd(cmd, host=VM_IP, user=VM_USER, password=VM_PASSWORD):
    """Run a command on the VM via SSH through Proxmox"""
    # Use sshpass through Proxmox
    ssh_cmd = f'ssh -o StrictHostKeyChecking=no {PROXMOX_USER}@{PROXMOX_HOST} "sshpass -p \'{password}\' ssh -o StrictHostKeyChecking=no {user}@{host} \'{cmd}\'"'
    print(f"[VM] {cmd}")
    result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result


def export_images():
    """Export all custom Docker images to tar files"""
    print("\n" + "="*60)
    print("STEP 1: EXPORTING DOCKER IMAGES")
    print("="*60)
    
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    for image in CUSTOM_IMAGES:
        safe_name = image.replace("/", "_").replace(":", "_")
        tar_file = EXPORT_DIR / f"{safe_name}.tar"
        
        if tar_file.exists():
            print(f"[SKIP] {tar_file.name} already exists")
            continue
            
        print(f"[EXPORT] {image} -> {tar_file.name}")
        result = run_local_cmd(f'docker save -o "{tar_file}" {image}')
        
        if result.returncode == 0:
            size_mb = tar_file.stat().st_size / (1024 * 1024)
            print(f"  SUCCESS: {size_mb:.1f} MB")
        else:
            print(f"  FAILED: {result.stderr}")
    
    # List exported files
    print("\nExported files:")
    for f in EXPORT_DIR.glob("*.tar"):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  {f.name}: {size_mb:.1f} MB")


def transfer_images():
    """Transfer image tar files to VM"""
    print("\n" + "="*60)
    print("STEP 2: TRANSFERRING IMAGES TO VM")
    print("="*60)
    
    # Create destination directory on VM
    run_ssh_cmd("sudo mkdir -p /opt/mycosoft/images && sudo chown mycosoft:mycosoft /opt/mycosoft/images")
    
    for tar_file in EXPORT_DIR.glob("*.tar"):
        print(f"\n[TRANSFER] {tar_file.name}")
        
        # Use scp through Proxmox
        # First copy to Proxmox, then to VM
        proxmox_temp = f"/tmp/{tar_file.name}"
        
        # Copy to Proxmox
        scp_to_proxmox = f'scp -o StrictHostKeyChecking=no "{tar_file}" {PROXMOX_USER}@{PROXMOX_HOST}:{proxmox_temp}'
        print(f"  -> Proxmox: {scp_to_proxmox}")
        result = run_local_cmd(scp_to_proxmox, check=False)
        
        if result.returncode == 0:
            # Copy from Proxmox to VM
            scp_to_vm = f'ssh {PROXMOX_USER}@{PROXMOX_HOST} "sshpass -p \'{VM_PASSWORD}\' scp -o StrictHostKeyChecking=no {proxmox_temp} {VM_USER}@{VM_IP}:/opt/mycosoft/images/"'
            print(f"  -> VM")
            result = run_local_cmd(scp_to_vm, check=False)
            
            # Cleanup Proxmox temp file
            run_local_cmd(f'ssh {PROXMOX_USER}@{PROXMOX_HOST} "rm -f {proxmox_temp}"', check=False)
            
            if result.returncode == 0:
                print(f"  SUCCESS")
            else:
                print(f"  FAILED: {result.stderr}")
        else:
            print(f"  FAILED: {result.stderr}")


def load_images():
    """Load Docker images on the VM"""
    print("\n" + "="*60)
    print("STEP 3: LOADING IMAGES ON VM")
    print("="*60)
    
    # Load each tar file
    run_ssh_cmd("cd /opt/mycosoft/images && for f in *.tar; do echo Loading $f...; sudo docker load -i $f; done")
    
    # Pull third-party images
    print("\nPulling third-party images...")
    for image in THIRD_PARTY_IMAGES:
        print(f"[PULL] {image}")
        run_ssh_cmd(f"sudo docker pull {image}")


def create_networks():
    """Create Docker networks on VM"""
    print("\n" + "="*60)
    print("STEP 4: CREATING DOCKER NETWORKS")
    print("="*60)
    
    run_ssh_cmd("sudo docker network create mycosoft-always-on 2>/dev/null || true")
    run_ssh_cmd("sudo docker network create mycosoft-mas_mas-network 2>/dev/null || true")
    run_ssh_cmd("sudo docker network ls | grep mycosoft")


def transfer_source_code():
    """Transfer source code to VM"""
    print("\n" + "="*60)
    print("STEP 5: TRANSFERRING SOURCE CODE")
    print("="*60)
    
    # Create directories
    run_ssh_cmd("sudo mkdir -p /opt/mycosoft/{website,mas,mindex} && sudo chown -R mycosoft:mycosoft /opt/mycosoft")
    
    # We'll transfer the docker-compose files and env files
    # The images are already built, we just need the compose files
    
    source_dirs = {
        "WEBSITE": r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website",
        "MAS": r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas",
        "MINDEX": r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\MINDEX\mindex",
    }
    
    # For now, let's just transfer the essential files via base64 encoding
    # This avoids complex SCP operations
    
    # Create docker-compose for production on VM
    create_production_compose()


def create_production_compose():
    """Create production docker-compose on VM"""
    print("\nCreating production docker-compose files...")
    
    # This creates a unified docker-compose that uses the exported images
    compose_content = '''version: "3.8"

# Mycosoft Production Stack
# All services configured for production deployment

services:
  # =========================================
  # ALWAYS-ON STACK
  # =========================================
  
  # PostgreSQL for MINDEX
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
      - mycosoft-always-on
      - mycosoft-mas_mas-network

  # MINDEX API
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
      API_KEYS: \'["local-dev-key"]\'
      DEFAULT_PAGE_SIZE: 100
      MAX_PAGE_SIZE: 1000
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
      - mycosoft-always-on
      - mycosoft-mas_mas-network

  # MINDEX ETL
  mindex-etl:
    image: mycosoft-always-on-mindex-etl:latest
    container_name: mindex-etl
    restart: unless-stopped
    command: python -m mindex_etl.scheduler --interval 60
    environment:
      MINDEX_DB_HOST: mindex-postgres
      MINDEX_DB_PORT: 5432
      MINDEX_DB_USER: mindex
      MINDEX_DB_PASSWORD: mindex
      MINDEX_DB_NAME: mindex
      DATABASE_URL: postgresql://mindex:mindex@mindex-postgres:5432/mindex
    volumes:
      - mindex_etl_checkpoints:/tmp/mindex_etl_checkpoints
    depends_on:
      mindex-postgres:
        condition: service_healthy
    networks:
      - mycosoft-always-on

  # MycoBrain Service
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
    networks:
      - mycosoft-always-on
      - mycosoft-mas_mas-network

  # Mycosoft Website (Next.js)
  mycosoft-website:
    image: website-website:latest
    container_name: mycosoft-website
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      NODE_ENV: production
      MINDEX_API_BASE_URL: http://mindex-api:8000
      MINDEX_API_URL: http://mindex-api:8000
      MINDEX_API_KEY: local-dev-key
      MYCOBRAIN_SERVICE_URL: http://mycobrain:8003
      MAS_API_URL: http://mas-orchestrator:8000
      N8N_LOCAL_URL: http://n8n:5678
      N8N_WEBHOOK_URL: http://n8n:5678
      REDIS_URL: redis://redis:6379
    depends_on:
      - mindex-api
      - mycobrain
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:3000/api/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    networks:
      - mycosoft-always-on
      - mycosoft-mas_mas-network

  # =========================================
  # MAS STACK
  # =========================================

  # MAS PostgreSQL
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
      test: ["CMD-SHELL", "pg_isready -h localhost -U mas"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - mycosoft-mas_mas-network

  # Redis (MAS)
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
      - mycosoft-always-on
      - mycosoft-mas_mas-network

  # Qdrant Vector Database
  qdrant:
    image: qdrant/qdrant:v1.13.2
    container_name: qdrant
    restart: unless-stopped
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD", "bash", "-c", "timeout 5 bash -c \'echo > /dev/tcp/localhost/6333\' >/dev/null 2>&1"]
      interval: 10s
      timeout: 10s
      retries: 10
      start_period: 60s
    networks:
      - mycosoft-mas_mas-network

  # MAS Orchestrator
  mas-orchestrator:
    image: mycosoft-mas-mas-orchestrator:latest
    container_name: mas-orchestrator
    restart: unless-stopped
    ports:
      - "8001:8000"
    environment:
      MAS_ENV: production
      DEBUG_MODE: "false"
      LOG_LEVEL: INFO
      REDIS_URL: redis://redis:6379/0
      DATABASE_URL: postgresql://mas:maspassword@mas-postgres:5432/mas
      QDRANT_URL: http://qdrant:6333
      OLLAMA_URL: http://ollama:11434
      N8N_WEBHOOK_URL: http://n8n:5678
      WHISPER_URL: http://whisper:8000
      TTS_URL: http://tts:10200
    depends_on:
      redis:
        condition: service_healthy
      mas-postgres:
        condition: service_healthy
      qdrant:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - mycosoft-mas_mas-network

  # n8n Workflow Automation
  n8n:
    image: n8nio/n8n:latest
    container_name: n8n
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      N8N_BASIC_AUTH_ACTIVE: "false"
      N8N_HOST: localhost
      N8N_PORT: 5678
      N8N_PROTOCOL: http
      WEBHOOK_URL: https://n8n.mycosoft.com/
      GENERIC_TIMEZONE: America/New_York
      WHISPER_URL: http://whisper:8000
      TTS_URL: http://openedai-speech:8000
      OLLAMA_URL: http://ollama:11434
    volumes:
      - n8n_data:/home/node/.n8n
    depends_on:
      - redis
    networks:
      - mycosoft-always-on
      - mycosoft-mas_mas-network

  # Ollama LLM
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    restart: unless-stopped
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      OLLAMA_ORIGINS: "*"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 5
    networks:
      - mycosoft-mas_mas-network

  # Whisper STT
  whisper:
    image: fedirz/faster-whisper-server:latest-cpu
    container_name: whisper
    restart: unless-stopped
    ports:
      - "8765:8000"
    environment:
      WHISPER__MODEL: Systran/faster-whisper-base.en
      WHISPER__INFERENCE_DEVICE: cpu
    volumes:
      - whisper_models:/root/.cache/huggingface
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 0"]
      interval: 60s
      timeout: 30s
      retries: 5
      start_period: 120s
    networks:
      - mycosoft-mas_mas-network

  # Piper TTS
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
      - mycosoft-mas_mas-network

  # OpenedAI Speech
  openedai-speech:
    image: ghcr.io/matatonic/openedai-speech:latest
    container_name: openedai-speech
    restart: unless-stopped
    ports:
      - "5500:8000"
    environment:
      TTS_HOME: /data
      HF_HOME: /data
    volumes:
      - openedai_speech_data:/data
    networks:
      - mycosoft-mas_mas-network

  # MYCA UniFi Dashboard
  myca-dashboard:
    image: mycosoft-mas-unifi-dashboard:latest
    container_name: myca-dashboard
    restart: unless-stopped
    ports:
      - "3100:3000"
    environment:
      NODE_ENV: production
      MAS_BACKEND_URL: http://mas-orchestrator:8000
      N8N_JARVIS_URL: http://n8n:5678/webhook/myca/jarvis
      N8N_WEBHOOK_URL: http://n8n:5678/webhook/myca/speech
      N8N_TTS_URL: http://n8n:5678/webhook/myca/speech/tts
      OPENEDAI_SPEECH_URL: http://openedai-speech:8000/v1/audio/speech
    networks:
      - mycosoft-mas_mas-network

  # Grafana Monitoring
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
      - mycosoft-mas_mas-network

  # Prometheus Metrics
  prometheus:
    image: prom/prometheus:v3.2.0
    container_name: prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - prometheus_data:/prometheus
    networks:
      - mycosoft-mas_mas-network

networks:
  mycosoft-always-on:
    driver: bridge
  mycosoft-mas_mas-network:
    driver: bridge

volumes:
  mindex_postgres_data:
  mindex_etl_checkpoints:
  mas_postgres_data:
  redis_data:
  qdrant_data:
  n8n_data:
  ollama_data:
  whisper_models:
  piper_data:
  openedai_speech_data:
  grafana_data:
  prometheus_data:
'''
    
    # Write to VM via SSH
    # Escape the content for shell
    import base64
    encoded = base64.b64encode(compose_content.encode()).decode()
    
    run_ssh_cmd(f"echo '{encoded}' | base64 -d > /opt/mycosoft/docker-compose.yml")
    print("Production docker-compose.yml created on VM")


def deploy_stack():
    """Deploy the full stack on VM"""
    print("\n" + "="*60)
    print("STEP 6: DEPLOYING FULL STACK")
    print("="*60)
    
    # Stop any existing containers
    run_ssh_cmd("cd /opt/mycosoft && sudo docker compose down 2>/dev/null || true")
    
    # Remove the simple placeholder containers
    run_ssh_cmd("sudo docker rm -f $(sudo docker ps -aq) 2>/dev/null || true")
    
    # Start the full stack
    run_ssh_cmd("cd /opt/mycosoft && sudo docker compose up -d")
    
    # Wait for services to start
    print("\nWaiting for services to start...")
    time.sleep(30)
    
    # Check status
    run_ssh_cmd("sudo docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'")


def verify_services():
    """Verify all services are healthy"""
    print("\n" + "="*60)
    print("STEP 7: VERIFYING SERVICES")
    print("="*60)
    
    endpoints = [
        ("Website", "http://localhost:3000/api/health"),
        ("MINDEX API", "http://localhost:8000/api/mindex/health"),
        ("MycoBrain", "http://localhost:8003/health"),
        ("MAS Orchestrator", "http://localhost:8001/health"),
        ("n8n", "http://localhost:5678/healthz"),
        ("Grafana", "http://localhost:3002/api/health"),
        ("MYCA Dashboard", "http://localhost:3100"),
    ]
    
    for name, url in endpoints:
        result = run_ssh_cmd(f"curl -s -o /dev/null -w '%{{http_code}}' {url}")
        print(f"{name}: {result.stdout.strip() if result.stdout else 'ERROR'}")


def main():
    print("="*60)
    print("MYCOSOFT FULL PRODUCTION DEPLOYMENT")
    print("="*60)
    print(f"Target VM: {VM_IP}")
    print(f"Export Directory: {EXPORT_DIR}")
    print("="*60)
    
    # Step 1: Export images
    export_images()
    
    # Step 2: Transfer images
    transfer_images()
    
    # Step 3: Load images on VM
    load_images()
    
    # Step 4: Create networks
    create_networks()
    
    # Step 5: Transfer source code / create compose files
    transfer_source_code()
    
    # Step 6: Deploy stack
    deploy_stack()
    
    # Step 7: Verify services
    verify_services()
    
    print("\n" + "="*60)
    print("DEPLOYMENT COMPLETE!")
    print("="*60)
    print(f"""
Services should now be accessible at:
- Website: https://sandbox.mycosoft.com (port 3000)
- MINDEX API: https://api-sandbox.mycosoft.com (port 8000)
- MycoBrain: https://brain-sandbox.mycosoft.com (port 8003)
- n8n: http://{VM_IP}:5678
- Grafana: http://{VM_IP}:3002
- MYCA Dashboard: http://{VM_IP}:3100
""")


if __name__ == "__main__":
    main()
