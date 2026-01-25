#!/usr/bin/env python3
"""
Force recreate the website container with the newly built image.
"""

import paramiko
import time
import sys

# VM Configuration
VM_HOST = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"

# Paths
MAS_PATH = "/home/mycosoft/mycosoft/mas"
COMPOSE_FILE = "docker-compose.always-on.yml"

def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    symbols = {"INFO": "→", "OK": "✓", "WARN": "⚠", "ERROR": "✗", "STEP": "▶"}
    print(f"[{ts}] {symbols.get(level, '→')} {msg}")

def run_ssh(ssh, cmd, timeout=120):
    """Run SSH command and return output."""
    log(f"Running: {cmd[:80]}...")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    output = stdout.read().decode('utf-8', errors='replace')
    error = stderr.read().decode('utf-8', errors='replace')
    exit_code = stdout.channel.recv_exit_status()
    if error and exit_code != 0:
        log(f"Error: {error[:200]}", "WARN")
    return output.strip(), exit_code

def main():
    print("\n" + "="*60)
    print("  FORCE RECREATE CONTAINER")
    print("="*60 + "\n")
    
    # Connect via SSH
    log("Connecting to VM via SSH...", "STEP")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
        log(f"Connected to {VM_HOST}", "OK")
    except Exception as e:
        log(f"SSH connection failed: {e}", "ERROR")
        return 1
    
    try:
        # Check current container
        log("Checking current container...", "STEP")
        output, _ = run_ssh(ssh, "docker ps --filter name=mycosoft-website --format '{{.ID}} {{.Image}} {{.Status}} {{.CreatedAt}}'")
        print(f"    Current: {output}")
        
        # Get current container ID
        container_id = output.split()[0] if output else None
        
        if container_id:
            # Stop the old container
            log("Stopping old container...", "STEP")
            run_ssh(ssh, f"docker stop {container_id}")
            
            # Remove the old container
            log("Removing old container...", "STEP")
            run_ssh(ssh, f"docker rm {container_id}")
        
        # Force recreate with new image
        log("Force recreating container with new image...", "STEP")
        output, code = run_ssh(ssh, f"cd {MAS_PATH} && docker compose -f {COMPOSE_FILE} up -d --force-recreate mycosoft-website", timeout=120)
        if code != 0:
            print(f"    Error: {output}")
        
        # Wait for healthy
        log("Waiting for container to be healthy (30s)...", "STEP")
        time.sleep(30)
        
        # Check new container
        log("Checking new container...", "STEP")
        output, _ = run_ssh(ssh, "docker ps --filter name=mycosoft-website --format '{{.ID}} {{.Image}} {{.Status}} {{.CreatedAt}}'")
        print(f"    New: {output}")
        
        # Verify it's responding
        log("Verifying container responds...", "STEP")
        output, _ = run_ssh(ssh, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
        log(f"Local HTTP: {output}", "OK")
        
        # Check container logs for errors
        log("Checking container logs for errors...", "STEP")
        output, _ = run_ssh(ssh, "docker logs mycosoft-website 2>&1 | tail -20")
        print(f"    Last logs:\n{output}")
        
    finally:
        ssh.close()
    
    print("\n" + "="*60)
    print("  CONTAINER RECREATED")
    print("="*60)
    print("\n⚠️  IMPORTANT: Manually purge Cloudflare cache:")
    print("    1. Go to https://dash.cloudflare.com")
    print("    2. Select mycosoft.com zone")
    print("    3. Go to Caching > Configuration")
    print("    4. Click 'Purge Everything'\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
