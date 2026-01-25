#!/usr/bin/env python3
"""
Direct SSH Deployment + Cloudflare Purge
Uses Paramiko for reliable SSH connection, bypassing Proxmox API
"""

import paramiko
import requests
import time
import sys

# VM Configuration
VM_HOST = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"

# Cloudflare Configuration
CF_ZONE_ID = "afd4d5ce84fb58d7a6e2fb98a207fbc6"
CF_API_TOKEN = "4YL2fJMqQBJiJQSVZqVVi-MF_cHTbnA1FVvEH8Dh"  # From previous successful deployments

# Paths
WEBSITE_PATH = "/home/mycosoft/mycosoft/website"
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
    print("  DIRECT SSH DEPLOYMENT + CLOUDFLARE PURGE")
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
        # Step 1: Pull latest code
        log("Pulling latest code from GitHub...", "STEP")
        output, code = run_ssh(ssh, f"cd {WEBSITE_PATH} && git fetch origin && git reset --hard origin/main")
        print(f"    {output[:200]}")
        
        # Step 2: Check current commit
        output, _ = run_ssh(ssh, f"cd {WEBSITE_PATH} && git log --oneline -1")
        log(f"Current commit: {output}", "OK")
        
        # Step 3: Clean Docker cache
        log("Cleaning Docker build cache...", "STEP")
        run_ssh(ssh, "docker builder prune -af", timeout=60)
        
        # Step 4: Stop and remove old container
        log("Stopping old container...", "STEP")
        run_ssh(ssh, f"cd {MAS_PATH} && docker compose -f {COMPOSE_FILE} stop mycosoft-website")
        run_ssh(ssh, f"cd {MAS_PATH} && docker compose -f {COMPOSE_FILE} rm -f mycosoft-website")
        
        # Step 5: Build new image
        log("Building Docker image (this takes 2-4 minutes)...", "STEP")
        output, code = run_ssh(ssh, f"cd {MAS_PATH} && docker compose -f {COMPOSE_FILE} build --no-cache mycosoft-website", timeout=300)
        if code != 0:
            log("Build failed - checking logs", "WARN")
            print(output[-500:])
        else:
            log("Docker image built successfully", "OK")
        
        # Step 6: Start container
        log("Starting container...", "STEP")
        run_ssh(ssh, f"cd {MAS_PATH} && docker compose -f {COMPOSE_FILE} up -d mycosoft-website")
        
        # Step 7: Wait for healthy
        log("Waiting for container to be healthy...", "STEP")
        time.sleep(15)
        output, _ = run_ssh(ssh, "docker ps --filter name=mycosoft-website --format '{{.Status}}'")
        log(f"Container status: {output}", "OK")
        
        # Step 8: Verify local response
        log("Verifying container responds...", "STEP")
        output, _ = run_ssh(ssh, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
        log(f"Local HTTP: {output}", "OK")
        
    finally:
        ssh.close()
    
    # Step 9: Purge Cloudflare cache
    log("Purging Cloudflare cache...", "STEP")
    try:
        cf_headers = {
            'Authorization': f'Bearer {CF_API_TOKEN}',
            'Content-Type': 'application/json'
        }
        cf_url = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/purge_cache'
        
        r = requests.post(cf_url, headers=cf_headers, json={'purge_everything': True}, timeout=30)
        
        if r.status_code == 200 and r.json().get('success'):
            log("Cloudflare cache purged successfully!", "OK")
        else:
            log(f"Cloudflare purge response: {r.status_code} - {r.text[:200]}", "WARN")
    except Exception as e:
        log(f"Cloudflare purge error: {e}", "ERROR")
    
    # Step 10: Verify sandbox
    log("Verifying sandbox.mycosoft.com...", "STEP")
    try:
        r = requests.get("https://sandbox.mycosoft.com", timeout=30, allow_redirects=True)
        log(f"Sandbox HTTP: {r.status_code}", "OK")
    except Exception as e:
        log(f"Sandbox verification failed: {e}", "WARN")
    
    print("\n" + "="*60)
    print("  DEPLOYMENT COMPLETE")
    print("="*60 + "\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
