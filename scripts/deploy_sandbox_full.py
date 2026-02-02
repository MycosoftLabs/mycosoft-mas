#!/usr/bin/env python3
"""
Full Sandbox Deployment Script - Feb 2, 2026
Deploys to sandbox.mycosoft.com with automatic Cloudflare cache purge

Usage:
    python scripts/deploy_sandbox_full.py

Environment Variables (set in .env or export):
    CLOUDFLARE_API_TOKEN - Token with Zone.Cache Purge permission
    CLOUDFLARE_ZONE_ID   - Zone ID for mycosoft.com (default: afd4d5ce84fb58d7a6e2fb98a207fbc6)
"""
import os
import sys
import io
import time
import requests
from pathlib import Path

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Load .env if exists
env_file = Path(__file__).parent.parent / '.env'
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if '=' in line and not line.startswith('#'):
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip())

# Configuration
SSH_HOST = "192.168.0.187"
SSH_USER = "mycosoft"
SSH_PASS = "REDACTED_VM_SSH_PASSWORD"

WEBSITE_REPO = "/opt/mycosoft/website"
MAS_REPO = "/home/mycosoft/mycosoft/mas"
COMPOSE_DIR = "/opt/mycosoft"

# Cloudflare
CF_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID", "af274016182495aeac049ac2c1f07b6d")
CF_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "BdvbQeLwi_yxOBUpJJIGF8eWmGKX-HQFKzn_aLkb")

def log(msg, level="INFO"):
    icons = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERROR": "❌", "STEP": "🔷"}
    print(f"{icons.get(level, '•')} [{level}] {msg}")

def run_ssh(client, cmd, timeout=120):
    """Run SSH command and return output"""
    log(f"Running: {cmd[:80]}...")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if out:
        print(f"    {out[:200]}")
    if err and "error" in err.lower():
        print(f"    STDERR: {err[:200]}")
    return out, err

def purge_cloudflare():
    """Purge Cloudflare cache"""
    if not CF_API_TOKEN:
        log("CLOUDFLARE_API_TOKEN not set - skipping cache purge", "WARN")
        log("To enable auto-purge:", "WARN")
        log("  1. Go to https://dash.cloudflare.com/profile/api-tokens", "WARN")
        log("  2. Create token with 'Zone.Cache Purge' permission", "WARN")
        log("  3. Add to .env: CLOUDFLARE_API_TOKEN=your_token", "WARN")
        return False
    
    log("Purging Cloudflare cache...", "STEP")
    try:
        headers = {
            'Authorization': f'Bearer {CF_API_TOKEN}',
            'Content-Type': 'application/json'
        }
        url = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/purge_cache'
        
        r = requests.post(url, headers=headers, json={'purge_everything': True}, timeout=30)
        
        if r.status_code == 200 and r.json().get('success'):
            log("Cloudflare cache purged!", "OK")
            return True
        else:
            log(f"Cloudflare purge failed: {r.status_code} - {r.text[:200]}", "ERROR")
            return False
    except Exception as e:
        log(f"Cloudflare purge error: {e}", "ERROR")
        return False

def main():
    try:
        import paramiko
    except ImportError:
        log("Installing paramiko...", "INFO")
        os.system("pip install paramiko")
        import paramiko
    
    print("\n" + "="*60)
    print("  MYCOSOFT SANDBOX DEPLOYMENT")
    print("  Target: sandbox.mycosoft.com (192.168.0.187)")
    print("="*60 + "\n")
    
    # Connect via SSH
    log("Connecting to sandbox VM...", "STEP")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=30)
    log("Connected!", "OK")
    
    # Update MAS repo
    log("Updating MAS repository...", "STEP")
    run_ssh(client, f"cd {MAS_REPO} && git fetch origin")
    run_ssh(client, f"cd {MAS_REPO} && git reset --hard origin/main")
    
    # Update Website repo
    log("Updating Website repository...", "STEP")
    run_ssh(client, f"cd {WEBSITE_REPO} && git fetch origin")
    run_ssh(client, f"cd {WEBSITE_REPO} && git reset --hard origin/main")
    
    # Rebuild website image
    log("Rebuilding website Docker image (2-5 minutes)...", "STEP")
    out, err = run_ssh(client, f"cd {WEBSITE_REPO} && docker build -t website-website:latest . 2>&1 | tail -5", timeout=600)
    
    # Restart container
    log("Restarting website container...", "STEP")
    run_ssh(client, "docker stop mycosoft-website 2>/dev/null; docker rm mycosoft-website 2>/dev/null")
    run_ssh(client, f"""docker run -d --name mycosoft-website \
        --restart unless-stopped \
        -p 3000:3000 \
        -v /opt/mycosoft/media/website/assets:/app/public/assets \
        -e NODE_ENV=production \
        --network mycosoft-production_mycosoft-network \
        website-website:latest""")
    
    # Wait for container to start
    log("Waiting for container health check...", "INFO")
    time.sleep(10)
    
    # Check status
    log("Checking container status...", "STEP")
    run_ssh(client, "docker ps --filter 'name=mycosoft-website' --format 'table {{.Names}}\t{{.Status}}'")
    
    # Test health endpoint
    log("Testing website health...", "STEP")
    out, _ = run_ssh(client, "curl -s http://localhost:3000/api/health | head -1")
    
    client.close()
    log("SSH connection closed", "OK")
    
    # Purge Cloudflare cache
    purge_cloudflare()
    
    # Final verification
    print("\n" + "="*60)
    log("DEPLOYMENT COMPLETE!", "OK")
    print("="*60)
    print("\n🌐 Verify at: https://sandbox.mycosoft.com")
    print("📋 Health: https://sandbox.mycosoft.com/api/health\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
