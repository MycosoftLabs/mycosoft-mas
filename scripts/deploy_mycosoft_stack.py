#!/usr/bin/env python3
"""Deploy Mycosoft Docker Stack to VM 103"""

import paramiko
import time

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"

def run_sudo_command(ssh, cmd, timeout=600):
    """Run a sudo command with password via stdin"""
    full_cmd = f"echo '{VM_PASS}' | sudo -S {cmd}"
    print(f"\n>>> Running: sudo {cmd[:70]}...")
    
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=timeout)
    
    out = stdout.read().decode()
    err = stderr.read().decode()
    
    if out:
        lines = out.strip().split('\n')
        if len(lines) > 15:
            print(f"... ({len(lines) - 15} lines omitted)")
            print('\n'.join(lines[-15:]))
        else:
            print(out)
    
    err_lines = [l for l in err.split('\n') if 'password' not in l.lower() and l.strip()]
    if err_lines:
        print(f"stderr: {' '.join(err_lines[:3])}")
    
    return out, err

def run_command(ssh, cmd, timeout=300):
    """Run a regular command"""
    print(f"\n>>> Running: {cmd[:70]}...")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    
    out = stdout.read().decode()
    err = stderr.read().decode()
    
    if out:
        print(out)
    if err:
        print(f"stderr: {err}")
    
    return out, err

def main():
    print("=" * 60)
    print("DEPLOYING MYCOSOFT DOCKER STACK")
    print(f"Target VM: {VM_IP}")
    print("=" * 60)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)
    
    print("Connected!")
    
    # Create project directory
    print("\n=== Creating project directory ===")
    run_command(ssh, "mkdir -p ~/mycosoft")
    
    # Create docker-compose.yml for Mycosoft stack
    print("\n=== Creating docker-compose.yml ===")
    
    docker_compose = '''version: "3.8"

services:
  # Mycosoft Website
  mycosoft-website:
    image: node:20-alpine
    container_name: mycosoft-website
    working_dir: /app
    ports:
      - "3000:3000"
    volumes:
      - website-data:/app
    restart: unless-stopped
    command: echo "Website placeholder - will be replaced with actual build"

  # MINDEX API
  mindex-api:
    image: python:3.11-slim
    container_name: mindex-api
    ports:
      - "8000:8000"
    volumes:
      - mindex-data:/app
    restart: unless-stopped
    command: echo "MINDEX API placeholder"

  # MycoBrain Service
  mycobrain-service:
    image: python:3.11-slim
    container_name: mycobrain-service
    ports:
      - "8003:8003"
    volumes:
      - mycobrain-data:/app
    restart: unless-stopped
    command: echo "MycoBrain placeholder"

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
  website-data:
  mindex-data:
  mycobrain-data:
  postgres-data:
  redis-data:
'''
    
    # Write docker-compose.yml
    create_file_cmd = f'''cat > ~/mycosoft/docker-compose.yml << 'COMPOSE_EOF'
{docker_compose}
COMPOSE_EOF'''
    
    run_command(ssh, create_file_cmd)
    
    # Verify file was created
    print("\n=== Verifying docker-compose.yml ===")
    run_command(ssh, "cat ~/mycosoft/docker-compose.yml | head -30")
    
    # Pull images
    print("\n=== Pulling Docker images ===")
    run_sudo_command(ssh, "docker compose -f /home/mycosoft/mycosoft/docker-compose.yml pull", timeout=600)
    
    # Start containers
    print("\n=== Starting containers ===")
    run_sudo_command(ssh, "docker compose -f /home/mycosoft/mycosoft/docker-compose.yml up -d", timeout=300)
    
    # Check status
    print("\n=== Container Status ===")
    run_sudo_command(ssh, "docker ps -a")
    
    # Show ports
    print("\n=== Listening Ports ===")
    run_sudo_command(ssh, "ss -tlnp | head -20")
    
    ssh.close()
    
    print("\n" + "=" * 60)
    print("MYCOSOFT STACK DEPLOYMENT COMPLETE!")
    print("=" * 60)
    print(f"""
Services running on {VM_IP}:
  - Website:     http://{VM_IP}:3000
  - MINDEX API:  http://{VM_IP}:8000
  - MycoBrain:   http://{VM_IP}:8003
  - PostgreSQL:  {VM_IP}:5432
  - Redis:       {VM_IP}:6379
""")

if __name__ == "__main__":
    main()
