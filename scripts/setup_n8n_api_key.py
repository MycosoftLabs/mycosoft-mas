#!/usr/bin/env python3
"""Setup n8n API key for workflow imports"""
import paramiko

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.0.188', username='mycosoft', password='Mushroom1!Mushroom1!')
    
    # Need to restart n8n with API key enabled
    print("=== Updating n8n configuration to enable API key ===")
    
    # Stop n8n
    print("Stopping n8n...")
    stdin, stdout, stderr = ssh.exec_command('cd /home/mycosoft/myca-integrations && docker compose stop n8n')
    stdout.channel.recv_exit_status()
    print(stdout.read().decode())
    
    # Update docker-compose with API key env
    print("Updating docker-compose with API configuration...")
    compose_update = '''
cat > /home/mycosoft/myca-integrations/docker-compose.yml << 'EOF'
version: '3.8'

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
      N8N_BASIC_AUTH_USER: admin
      N8N_BASIC_AUTH_PASSWORD: Mushroom1!
      N8N_PUBLIC_API_DISABLED: "false"
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
EOF
'''
    stdin, stdout, stderr = ssh.exec_command(compose_update)
    stdout.channel.recv_exit_status()
    
    # Start n8n
    print("Starting n8n...")
    stdin, stdout, stderr = ssh.exec_command('cd /home/mycosoft/myca-integrations && docker compose up -d n8n')
    stdout.channel.recv_exit_status()
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    # Wait for n8n to start
    import time
    print("Waiting for n8n to start...")
    time.sleep(15)
    
    # Check status
    print("\n=== n8n Status ===")
    stdin, stdout, stderr = ssh.exec_command('docker ps | grep n8n')
    print(stdout.read().decode())
    
    # Create API key using n8n CLI
    print("\n=== Creating API key using n8n CLI ===")
    stdin, stdout, stderr = ssh.exec_command('docker exec myca-n8n n8n user-management:create-api-key --id=1 2>&1 || echo "API key creation via CLI not available"')
    result = stdout.read().decode()
    print(result)
    
    # Alternative: access via cookie-based auth
    print("\n=== Alternative: Use cookie session ===")
    print("Since n8n requires API key creation through UI, you need to:")
    print("1. Go to http://192.168.0.188:5678")
    print("2. Login with admin / Mushroom1!")
    print("3. Go to Settings > n8n API")
    print("4. Create a new API key")
    print("5. Add the key to .env.local as N8N_LOCAL_API_KEY")
    
    ssh.close()
    print("\nDone!")

if __name__ == "__main__":
    main()
