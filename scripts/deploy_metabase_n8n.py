#!/usr/bin/env python3
"""
Deploy Metabase + n8n to MAS VM for MYCA Integration
Date: January 27, 2026
"""

import paramiko
import time

DOCKER_COMPOSE_CONTENT = '''
# Metabase + n8n Integration Stack for MYCA
# Date: January 27, 2026

version: '3.8'

services:
  # Metabase - Business Intelligence & Natural Language Queries
  metabase:
    image: metabase/metabase:latest
    container_name: myca-metabase
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      MB_DB_TYPE: postgres
      MB_DB_DBNAME: metabase
      MB_DB_PORT: 5432
      MB_DB_USER: metabase
      MB_DB_PASS: MetabasePass123!
      MB_DB_HOST: metabase-db
      MB_SITE_NAME: MYCA Intelligence
      MB_SITE_URL: http://192.168.0.188:3000
      MB_ADMIN_EMAIL: morgan@mycosoft.org
      MB_ANON_TRACKING_ENABLED: "false"
    volumes:
      - metabase-data:/metabase-data
    depends_on:
      metabase-db:
        condition: service_healthy
    networks:
      - myca-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 120s

  # PostgreSQL for Metabase internal storage
  metabase-db:
    image: postgres:15-alpine
    container_name: myca-metabase-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: metabase
      POSTGRES_PASSWORD: MetabasePass123!
      POSTGRES_DB: metabase
    volumes:
      - metabase-db-data:/var/lib/postgresql/data
    networks:
      - myca-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U metabase"]
      interval: 10s
      timeout: 5s
      retries: 5

  # n8n Workflow Engine - For MYCA Voice & Chat Workflows
  n8n:
    image: n8nio/n8n:latest
    container_name: myca-n8n
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      DB_TYPE: sqlite
      DB_SQLITE_DATABASE: /home/node/.n8n/database.sqlite
      WEBHOOK_URL: http://192.168.0.188:5678/
      N8N_HOST: 0.0.0.0
      N8N_PORT: 5678
      N8N_BASIC_AUTH_ACTIVE: "true"
      N8N_BASIC_AUTH_USER: admin
      N8N_BASIC_AUTH_PASSWORD: Mushroom1!
      EXECUTIONS_PROCESS: main
      EXECUTIONS_DATA_SAVE_ON_ERROR: all
      EXECUTIONS_DATA_SAVE_ON_SUCCESS: all
      EXECUTIONS_DATA_SAVE_MANUAL_EXECUTIONS: "true"
      GENERIC_TIMEZONE: America/Los_Angeles
      TZ: America/Los_Angeles
      N8N_METRICS: "true"
    volumes:
      - n8n-data:/home/node/.n8n
    networks:
      - myca-network
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:5678/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

volumes:
  metabase-data:
  metabase-db-data:
  n8n-data:

networks:
  myca-network:
    driver: bridge
    name: myca-integration-network
'''

def main():
    print("=== Deploying Metabase + n8n to MAS VM ===")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.0.188', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD')
    
    # Create directory
    print("Creating deployment directory...")
    stdin, stdout, stderr = ssh.exec_command('mkdir -p /home/mycosoft/myca-integrations')
    stdout.channel.recv_exit_status()
    
    # Write docker-compose file
    print("Writing docker-compose file...")
    sftp = ssh.open_sftp()
    with sftp.file('/home/mycosoft/myca-integrations/docker-compose.yml', 'w') as f:
        f.write(DOCKER_COMPOSE_CONTENT)
    sftp.close()
    
    # Pull images first
    print("Pulling Docker images (this may take a few minutes)...")
    stdin, stdout, stderr = ssh.exec_command('cd /home/mycosoft/myca-integrations && docker compose pull')
    exit_status = stdout.channel.recv_exit_status()
    print(stdout.read().decode())
    if stderr.channel.recv_exit_status() != 0:
        print(stderr.read().decode())
    
    # Start containers
    print("Starting containers...")
    stdin, stdout, stderr = ssh.exec_command('cd /home/mycosoft/myca-integrations && docker compose up -d')
    exit_status = stdout.channel.recv_exit_status()
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print("STDERR:", err)
    
    # Wait for containers to start
    print("Waiting for containers to initialize (30s)...")
    time.sleep(30)
    
    # Check status
    print("Checking container status...")
    stdin, stdout, stderr = ssh.exec_command('docker ps --filter "name=myca-" --format "table {{.Names}}\\t{{.Status}}"')
    print(stdout.read().decode())
    
    # Check if services are responding
    print("Testing Metabase (port 3000)...")
    stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/health 2>/dev/null || echo "Not ready yet"')
    print(f"Metabase: {stdout.read().decode()}")
    
    print("Testing n8n (port 5678)...")
    stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost:5678/healthz 2>/dev/null || echo "Not ready yet"')
    print(f"n8n: {stdout.read().decode()}")
    
    ssh.close()
    
    print("\n=== Deployment Complete ===")
    print("Metabase: http://192.168.0.188:3000")
    print("n8n: http://192.168.0.188:5678 (admin / Mushroom1!)")
    print("\nNote: Metabase may take 2-3 minutes to fully initialize on first run.")

if __name__ == "__main__":
    main()
