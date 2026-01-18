#!/usr/bin/env python3
"""
Full Mycosoft System Deployment Script
=======================================
This script deploys the complete Mycosoft system to VM 103.

Based on documentation:
- docs/COMPLETE_VM_DEPLOYMENT_GUIDE.md
- docs/SERVER_MIGRATION_MASTER_GUIDE.md
- docs/MYCOSOFT_STACK_DEPLOYMENT.md

Deployment Order:
1. Prepare VM directories
2. Transfer codebases
3. Configure environment
4. Start MAS stack FIRST (n8n, redis, orchestrator)
5. Start Website stack SECOND
6. Connect networks
7. Verify deployment
"""

import subprocess
import os
import sys
import time

# Configuration
VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"
PROXMOX_HOST = "192.168.0.202"

# Windows paths to codebases
WEBSITE_PATH = r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website"
MAS_PATH = r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"
MINDEX_PATH = r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\MINDEX"

# VM paths
VM_BASE = "/opt/mycosoft"
VM_WEBSITE = f"{VM_BASE}/website"
VM_MAS = f"{VM_BASE}/mas"
VM_DATA = f"{VM_BASE}/data"

def run_ssh_command(command, description=""):
    """Run a command on the VM via SSH through Proxmox"""
    print(f"\n[*] {description}" if description else f"\n[*] Running: {command[:50]}...")
    
    # Build the SSH chain: Windows -> Proxmox -> VM
    ssh_cmd = f'''ssh -o StrictHostKeyChecking=no root@{PROXMOX_HOST} "sshpass -p '{VM_PASSWORD}' ssh -o StrictHostKeyChecking=no {VM_USER}@{VM_IP} '{command}'"'''
    
    result = subprocess.run(
        ["powershell", "-Command", ssh_cmd],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"    [OK] Success")
        if result.stdout.strip():
            print(f"    Output: {result.stdout.strip()[:200]}")
    else:
        print(f"    [!] Error: {result.stderr.strip()[:200]}")
    
    return result


def step_1_prepare_directories():
    """Create directory structure on VM"""
    print("\n" + "="*60)
    print("STEP 1: Preparing VM Directory Structure")
    print("="*60)
    
    commands = [
        f"sudo mkdir -p {VM_WEBSITE}",
        f"sudo mkdir -p {VM_MAS}",
        f"sudo mkdir -p {VM_DATA}/postgres",
        f"sudo mkdir -p {VM_DATA}/redis",
        f"sudo mkdir -p {VM_DATA}/qdrant",
        f"sudo mkdir -p {VM_DATA}/n8n",
        f"sudo mkdir -p {VM_DATA}/mindex",
        f"sudo mkdir -p {VM_BASE}/logs",
        f"sudo mkdir -p {VM_BASE}/backups",
        f"sudo mkdir -p {VM_BASE}/config",
        f"sudo chown -R {VM_USER}:{VM_USER} {VM_BASE}",
        f"sudo chmod -R 755 {VM_BASE}",
    ]
    
    for cmd in commands:
        run_ssh_command(cmd, f"Creating: {cmd.split()[-1]}")


def step_2_stop_placeholder_containers():
    """Stop the placeholder containers we deployed earlier"""
    print("\n" + "="*60)
    print("STEP 2: Stopping Placeholder Containers")
    print("="*60)
    
    run_ssh_command(
        "cd /home/mycosoft/mycosoft && docker compose down 2>/dev/null || true",
        "Stopping placeholder containers"
    )
    
    # Also clean up any dangling containers
    run_ssh_command(
        "docker container prune -f 2>/dev/null || true",
        "Cleaning up old containers"
    )


def step_3_transfer_codebases():
    """Transfer codebases from Windows to VM"""
    print("\n" + "="*60)
    print("STEP 3: Transferring Codebases")
    print("="*60)
    
    # This is more complex - we need to use SCP through Proxmox
    # or rsync. Let's use a tar+scp approach.
    
    print("\n[!] MANUAL STEP REQUIRED:")
    print("    Due to file transfer complexity, please run these commands manually:")
    print()
    print("    Option A - From Windows PowerShell (if you have OpenSSH):")
    print(f'    scp -r "{WEBSITE_PATH}\\*" {VM_USER}@{VM_IP}:{VM_WEBSITE}/')
    print(f'    scp -r "{MAS_PATH}\\*" {VM_USER}@{VM_IP}:{VM_MAS}/')
    print()
    print("    Option B - Using rsync via WSL:")
    print(f'    rsync -avz --progress "{WEBSITE_PATH}/" {VM_USER}@{VM_IP}:{VM_WEBSITE}/')
    print(f'    rsync -avz --progress "{MAS_PATH}/" {VM_USER}@{VM_IP}:{VM_MAS}/')
    print()
    print("    Option C - Copy through Proxmox host:")
    print(f"    1. SCP to Proxmox: scp -r {WEBSITE_PATH} root@{PROXMOX_HOST}:/tmp/website/")
    print(f"    2. Then Proxmox to VM: ssh root@{PROXMOX_HOST} 'scp -r /tmp/website/* {VM_USER}@{VM_IP}:{VM_WEBSITE}/'")
    print()
    
    input("Press Enter after you've transferred the files...")


def step_4_configure_environment():
    """Configure environment files on VM"""
    print("\n" + "="*60)
    print("STEP 4: Configuring Environment Files")
    print("="*60)
    
    # Create MAS .env file
    mas_env = '''# MAS Environment Configuration
# Database
POSTGRES_USER=mycosoft
POSTGRES_PASSWORD=MycoSecure2026!
POSTGRES_DB=mycosoft_mas
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://redis:6379
REDIS_HOST=redis
REDIS_PORT=6379

# n8n Configuration
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=Mycosoft2026!
N8N_HOST=0.0.0.0
N8N_PORT=5678
N8N_PROTOCOL=http
N8N_ENCRYPTION_KEY=mycosoft_n8n_encryption_key_2026

# Orchestrator
ORCHESTRATOR_PORT=8001
ORCHESTRATOR_HOST=0.0.0.0

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# Ollama
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama3.1:8b

# Voice Services
WHISPER_HOST=whisper
TTS_HOST=piper-tts
SPEECH_HOST=openedai-speech

# General
NODE_ENV=production
LOG_LEVEL=info
'''
    
    # Create Website .env.local file
    website_env = '''# Website Environment Configuration
# Database
POSTGRES_URL=postgresql://mycosoft:MycoSecure2026!@postgres:5432/mycosoft
POSTGRES_PASSWORD=MycoSecure2026!

# Cache
REDIS_URL=redis://mycosoft-mas-redis-1:6379

# MINDEX Integration
MINDEX_API_URL=http://mindex-api:8000
MINDEX_API_KEY=mindex_sandbox_key_2026

# N8N Integration
N8N_LOCAL_URL=http://mycosoft-mas-n8n-1:5678
N8N_WEBHOOK_URL=http://mycosoft-mas-n8n-1:5678

# Authentication
NEXTAUTH_SECRET=mycosoft_nextauth_secret_32_chars_minimum
NEXTAUTH_URL=https://sandbox.mycosoft.com

# Public URLs
NEXT_PUBLIC_SITE_URL=https://sandbox.mycosoft.com
NEXT_PUBLIC_API_URL=https://api-sandbox.mycosoft.com

# General
NODE_ENV=production
'''
    
    # Write .env files via SSH
    run_ssh_command(
        f"cat > {VM_MAS}/.env << 'ENVEOF'\n{mas_env}\nENVEOF",
        "Creating MAS .env file"
    )
    
    run_ssh_command(
        f"cat > {VM_WEBSITE}/.env.local << 'ENVEOF'\n{website_env}\nENVEOF",
        "Creating Website .env.local file"
    )


def step_5_create_docker_networks():
    """Create required Docker networks"""
    print("\n" + "="*60)
    print("STEP 5: Creating Docker Networks")
    print("="*60)
    
    run_ssh_command(
        "docker network create mycosoft-always-on 2>/dev/null || true",
        "Creating mycosoft-always-on network"
    )
    
    run_ssh_command(
        "docker network create mycosoft-mas_mas-network 2>/dev/null || true",
        "Creating mycosoft-mas_mas-network"
    )


def step_6_start_mas_stack():
    """Start MAS stack first (contains n8n and redis that website needs)"""
    print("\n" + "="*60)
    print("STEP 6: Starting MAS Stack (FIRST)")
    print("="*60)
    
    run_ssh_command(
        f"cd {VM_MAS} && docker compose up -d --build",
        "Building and starting MAS stack"
    )
    
    print("    Waiting 30 seconds for services to initialize...")
    time.sleep(30)
    
    # Verify n8n is running
    run_ssh_command(
        "curl -s http://localhost:5678/healthz || echo 'n8n not ready yet'",
        "Checking n8n health"
    )


def step_7_start_website_stack():
    """Start Website/Always-On stack second"""
    print("\n" + "="*60)
    print("STEP 7: Starting Website Stack (SECOND)")
    print("="*60)
    
    # First, check if always-on compose file exists
    run_ssh_command(
        f"cd {VM_WEBSITE} && docker compose -f docker-compose.always-on.yml up -d --build 2>/dev/null || docker compose up -d --build",
        "Building and starting Website stack"
    )
    
    print("    Waiting 20 seconds for website to start...")
    time.sleep(20)


def step_8_connect_networks():
    """Connect containers to both networks for n8n integration"""
    print("\n" + "="*60)
    print("STEP 8: Connecting Docker Networks")
    print("="*60)
    
    # Connect n8n and redis to always-on network
    run_ssh_command(
        "docker network connect mycosoft-always-on mycosoft-mas-n8n-1 2>/dev/null || true",
        "Connecting n8n to always-on network"
    )
    
    run_ssh_command(
        "docker network connect mycosoft-always-on mycosoft-mas-redis-1 2>/dev/null || true",
        "Connecting redis to always-on network"
    )


def step_9_verify_deployment():
    """Verify all services are running"""
    print("\n" + "="*60)
    print("STEP 9: Verifying Deployment")
    print("="*60)
    
    checks = [
        ("Website (3000)", "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/health 2>/dev/null || echo 'DOWN'"),
        ("MINDEX API (8000)", "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health 2>/dev/null || echo 'DOWN'"),
        ("MAS Orchestrator (8001)", "curl -s -o /dev/null -w '%{http_code}' http://localhost:8001/health 2>/dev/null || echo 'DOWN'"),
        ("n8n (5678)", "curl -s -o /dev/null -w '%{http_code}' http://localhost:5678/healthz 2>/dev/null || echo 'DOWN'"),
        ("MycoBrain (8003)", "curl -s -o /dev/null -w '%{http_code}' http://localhost:8003/health 2>/dev/null || echo 'DOWN'"),
        ("Grafana (3002)", "curl -s -o /dev/null -w '%{http_code}' http://localhost:3002/api/health 2>/dev/null || echo 'DOWN'"),
    ]
    
    print("\n--- Service Health Checks ---")
    for name, cmd in checks:
        run_ssh_command(cmd, f"Checking {name}")
    
    # Show running containers
    print("\n--- Running Containers ---")
    run_ssh_command(
        "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | head -20",
        "Container status"
    )


def step_10_show_next_steps():
    """Display next steps for the user"""
    print("\n" + "="*60)
    print("DEPLOYMENT COMPLETE!")
    print("="*60)
    
    print("""
Next Steps:
-----------
1. Access the services:
   - Website: http://192.168.0.187:3000
   - CREP Dashboard: http://192.168.0.187:3000/dashboard/crep
   - n8n Workflows: http://192.168.0.187:5678 (admin/Mycosoft2026!)
   - Grafana: http://192.168.0.187:3002
   - MAS Orchestrator: http://192.168.0.187:8001

2. Update Cloudflare Tunnel (already running):
   - The tunnel needs to point to the real services now
   - sandbox.mycosoft.com -> http://localhost:3000
   - api-sandbox.mycosoft.com -> http://localhost:8000
   - brain-sandbox.mycosoft.com -> http://localhost:8003

3. Public Access:
   - https://sandbox.mycosoft.com
   - https://api-sandbox.mycosoft.com
   - https://brain-sandbox.mycosoft.com

4. SSH Access:
   ssh mycosoft@192.168.0.187

5. View Logs:
   docker compose logs -f
""")


def main():
    """Main deployment orchestration"""
    print("="*60)
    print("MYCOSOFT FULL SYSTEM DEPLOYMENT")
    print("="*60)
    print(f"Target VM: {VM_IP}")
    print(f"User: {VM_USER}")
    print("="*60)
    
    try:
        step_1_prepare_directories()
        step_2_stop_placeholder_containers()
        step_3_transfer_codebases()  # Manual step
        step_4_configure_environment()
        step_5_create_docker_networks()
        step_6_start_mas_stack()
        step_7_start_website_stack()
        step_8_connect_networks()
        step_9_verify_deployment()
        step_10_show_next_steps()
        
    except KeyboardInterrupt:
        print("\n\n[!] Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[!] Error during deployment: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
