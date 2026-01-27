#!/usr/bin/env python3
"""
Fix n8n secure cookie issue
Date: January 27, 2026
"""
import paramiko
import time

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.0.188', username='mycosoft', password='REDACTED_VM_SSH_PASSWORD')
    
    print("=== Fixing n8n secure cookie ===")
    
    # Stop n8n container
    print("Stopping n8n...")
    stdin, stdout, stderr = ssh.exec_command('cd /home/mycosoft/myca-integrations && docker compose stop n8n')
    stdout.channel.recv_exit_status()
    
    # Update docker-compose with secure cookie disabled
    print("Updating n8n configuration...")
    compose_content = '''version: '3.8'

services:
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
      N8N_BASIC_AUTH_USER: morgan@mycosoft.org
      N8N_BASIC_AUTH_PASSWORD: "REDACTED_VM_SSH_PASSWORD"
      N8N_PUBLIC_API_DISABLED: "false"
      N8N_SECURE_COOKIE: "false"
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
    
    # Write compose file
    cmd = f'''cat > /home/mycosoft/myca-integrations/docker-compose.yml << 'COMPOSE_EOF'
{compose_content}
COMPOSE_EOF'''
    
    stdin, stdout, stderr = ssh.exec_command(cmd)
    stdout.channel.recv_exit_status()
    
    # Restart n8n
    print("Starting n8n with secure cookie disabled...")
    stdin, stdout, stderr = ssh.exec_command('cd /home/mycosoft/myca-integrations && docker compose up -d n8n')
    stdout.channel.recv_exit_status()
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    # Wait for n8n to start
    print("Waiting for n8n to start...")
    time.sleep(10)
    
    # Check status
    print("\n=== n8n Status ===")
    stdin, stdout, stderr = ssh.exec_command('docker ps | grep n8n')
    print(stdout.read().decode())
    
    ssh.close()
    print("\nDone! Try accessing http://192.168.0.188:5678 again")


if __name__ == "__main__":
    main()
