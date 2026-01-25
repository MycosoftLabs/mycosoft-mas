#!/usr/bin/env python3
"""
Deploy Mycorrhizae Protocol to the Sandbox VM

This script:
1. Pushes the Mycorrhizae Protocol code to the VM
2. Builds and starts the Docker container
3. Verifies health and API endpoints
"""

import paramiko
import json
import time
import sys
import os

# Configuration
VM_IP = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASSWORD = 'Mushroom1!Mushroom1!'

MYCORRHIZAE_PATH = r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\Mycorrhizae\mycorrhizae-protocol"


def run_ssh_cmd(ssh_client, cmd, timeout=120):
    """Run SSH command and return output."""
    try:
        stdin, stdout, stderr = ssh_client.exec_command(cmd, timeout=timeout)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='replace').strip()
        error = stderr.read().decode('utf-8', errors='replace').strip()
        if exit_status != 0 and error:
            print(f"    [stderr] {error}")
        return output, error, exit_status
    except paramiko.SSHException as e:
        print(f"    [SSH Error] {e}")
        return "", str(e), 1
    except Exception as e:
        print(f"    [Error] {e}")
        return "", str(e), 1


def connect_to_vm():
    """Connect to VM via SSH."""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        print(f"[{time.strftime('%H:%M:%S')}] ▶ Connecting to VM...")
        ssh_client.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=10)
        print(f"[{time.strftime('%H:%M:%S')}] ✓ Connected to {VM_IP}")
        return ssh_client
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ❌ Failed to connect to VM: {e}")
        sys.exit(1)


def upload_directory(sftp, local_path, remote_path):
    """Upload a directory recursively via SFTP."""
    import os
    
    # Create remote directory if it doesn't exist
    try:
        sftp.mkdir(remote_path)
    except:
        pass  # Directory might already exist
    
    for item in os.listdir(local_path):
        local_item = os.path.join(local_path, item)
        remote_item = f"{remote_path}/{item}"
        
        if os.path.isdir(local_item):
            # Skip __pycache__ and .git
            if item in ['__pycache__', '.git', '.pytest_cache', '.ruff_cache', 'venv', '.venv']:
                continue
            upload_directory(sftp, local_item, remote_item)
        else:
            # Skip .pyc files
            if item.endswith('.pyc'):
                continue
            print(f"    Uploading: {item}")
            sftp.put(local_item, remote_item)


def main():
    print("\n======================================================================")
    print("     MYCORRHIZAE PROTOCOL DEPLOYMENT")
    print("     Deploy to Sandbox VM")
    print("======================================================================\n")
    
    ssh = connect_to_vm()
    sftp = ssh.open_sftp()
    
    # Step 1: Create deployment directory
    print(f"\n[{time.strftime('%H:%M:%S')}] ▶ Creating deployment directory...")
    run_ssh_cmd(ssh, "mkdir -p /home/mycosoft/mycorrhizae-protocol")
    
    # Step 2: Upload source code
    print(f"\n[{time.strftime('%H:%M:%S')}] ▶ Uploading Mycorrhizae Protocol source code...")
    upload_directory(sftp, MYCORRHIZAE_PATH, "/home/mycosoft/mycorrhizae-protocol")
    print(f"[{time.strftime('%H:%M:%S')}] ✓ Source code uploaded")
    
    # Step 3: Create optimized docker-compose for VM deployment
    print(f"\n[{time.strftime('%H:%M:%S')}] ▶ Creating VM-optimized docker-compose...")
    
    docker_compose_content = '''version: "3.8"

services:
  mycorrhizae-api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: mycorrhizae-api
    ports:
      - "8002:8002"
    environment:
      # Connect to existing mindex-postgres-data on host network
      - MYCORRHIZAE_DATABASE_URL=postgresql://mindex:mindex@host.docker.internal:5434/mindex
      - MYCORRHIZAE_REDIS_URL=redis://redis:6379
      - MYCORRHIZAE_HOST=0.0.0.0
      - MYCORRHIZAE_PORT=8002
    extra_hosts:
      - "host.docker.internal:host-gateway"
    networks:
      - mycorrhizae-net
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s

  redis:
    image: redis:7-alpine
    container_name: mycorrhizae-redis
    ports:
      - "6380:6379"
    volumes:
      - redis-data:/data
    networks:
      - mycorrhizae-net
    restart: unless-stopped
    command: redis-server --appendonly yes

networks:
  mycorrhizae-net:
    driver: bridge

volumes:
  redis-data:
'''
    
    # Write docker-compose.vm.yml
    with sftp.file("/home/mycosoft/mycorrhizae-protocol/docker-compose.vm.yml", "w") as f:
        f.write(docker_compose_content)
    
    print(f"[{time.strftime('%H:%M:%S')}] ✓ docker-compose.vm.yml created")
    
    # Step 4: Stop any existing containers
    print(f"\n[{time.strftime('%H:%M:%S')}] ▶ Stopping existing containers...")
    run_ssh_cmd(ssh, "docker stop mycorrhizae-api mycorrhizae-redis 2>/dev/null || true")
    run_ssh_cmd(ssh, "docker rm mycorrhizae-api mycorrhizae-redis 2>/dev/null || true")
    
    # Step 5: Build and start
    print(f"\n[{time.strftime('%H:%M:%S')}] ▶ Building Mycorrhizae API Docker image...")
    output, error, status = run_ssh_cmd(
        ssh,
        "cd /home/mycosoft/mycorrhizae-protocol && docker compose -f docker-compose.vm.yml build --no-cache",
        timeout=300
    )
    if status != 0:
        print(f"[{time.strftime('%H:%M:%S')}] ⚠ Build issues (continuing): {error[:200] if error else ''}")
    else:
        print(f"[{time.strftime('%H:%M:%S')}] ✓ Docker image built")
    
    print(f"\n[{time.strftime('%H:%M:%S')}] ▶ Starting Mycorrhizae services...")
    output, error, status = run_ssh_cmd(
        ssh,
        "cd /home/mycosoft/mycorrhizae-protocol && docker compose -f docker-compose.vm.yml up -d",
        timeout=120
    )
    if status != 0:
        print(f"[{time.strftime('%H:%M:%S')}] ❌ Failed to start services: {error}")
    else:
        print(f"[{time.strftime('%H:%M:%S')}] ✓ Services started")
    
    # Step 6: Wait for services to be ready
    print(f"\n[{time.strftime('%H:%M:%S')}] ⏳ Waiting for services to be ready (20s)...")
    time.sleep(20)
    
    # Step 7: Check container status
    print(f"\n[{time.strftime('%H:%M:%S')}] ▶ Checking container status...")
    output, _, _ = run_ssh_cmd(ssh, "docker ps --format '{{.Names}}\\t{{.Status}}' | grep -E '(mycorrhizae|mindex)'")
    for line in output.splitlines():
        print(f"    {line}")
    
    # Step 8: Test health endpoint
    print(f"\n[{time.strftime('%H:%M:%S')}] ▶ Testing Mycorrhizae API health...")
    output, error, status = run_ssh_cmd(ssh, "curl -s http://localhost:8002/health")
    if status == 0 and output:
        print(f"    {output}")
    else:
        print(f"    ⚠ Health check failed: {error or 'No response'}")
        # Check logs
        print(f"\n[{time.strftime('%H:%M:%S')}] ▶ Checking container logs...")
        logs, _, _ = run_ssh_cmd(ssh, "docker logs mycorrhizae-api --tail 30 2>&1")
        print(f"    {logs}")
    
    # Step 9: Test API info
    print(f"\n[{time.strftime('%H:%M:%S')}] ▶ Testing API info endpoint...")
    output, _, _ = run_ssh_cmd(ssh, "curl -s http://localhost:8002/api/info")
    if output:
        print(f"    {output}")
    
    # Cleanup
    sftp.close()
    ssh.close()
    
    print("\n======================================================================")
    print("     DEPLOYMENT COMPLETE")
    print("======================================================================")
    print(f"\n    Mycorrhizae API: http://{VM_IP}:8002")
    print(f"    Health Check:    http://{VM_IP}:8002/health")
    print(f"    API Docs:        http://{VM_IP}:8002/docs")
    print(f"    API Info:        http://{VM_IP}:8002/api/info")
    print(f"    API Stats:       http://{VM_IP}:8002/api/stats")
    print("\n")


if __name__ == "__main__":
    main()
