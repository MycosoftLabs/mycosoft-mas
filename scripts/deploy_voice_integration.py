#!/usr/bin/env python3
"""
Deploy MYCA Orchestrator Memory Integration - February 3, 2026

Deploys the new voice and memory features to:
- Sandbox VM (192.168.0.187)
- MAS VM (192.168.0.188)
"""
import paramiko
import time
import sys

SANDBOX_IP = "192.168.0.187"
MAS_VM_IP = "192.168.0.188"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"

def run_cmd(ssh, cmd, sudo=False, timeout=300):
    if sudo:
        cmd = f"echo '{VM_PASS}' | sudo -S {cmd}"
    print(f">>> {cmd[:80]}...")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out:
        for line in out.strip().split('\n')[-5:]:
            safe_line = line.encode('ascii', errors='replace').decode('ascii')
            print(f"    {safe_line}")
    if err and "password" not in err.lower():
        safe_err = err[:100].encode('ascii', errors='replace').decode('ascii')
        print(f"    ERR: {safe_err}")
    return out, err

def deploy_to_vm(ip, name):
    print("=" * 70)
    print(f"DEPLOYING TO {name} ({ip})")
    print("=" * 70)
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=VM_USER, password=VM_PASS, timeout=30)
        print("Connected!")
        
        # Pull latest MAS code
        print("\n[1/4] Pulling MAS updates...")
        run_cmd(ssh, "cd /opt/mycosoft/mas && git reset --hard origin/main && git pull origin main")
        
        # Pull latest Website code  
        print("\n[2/4] Pulling Website updates...")
        run_cmd(ssh, "cd /opt/mycosoft/website && git reset --hard origin/main && git pull origin main")
        
        # Rebuild website container
        print("\n[3/4] Rebuilding website container...")
        run_cmd(ssh, "cd /opt/mycosoft/website && docker compose -f docker-compose.always-on.yml build mycosoft-website --no-cache", sudo=True, timeout=600)
        
        # Restart services
        print("\n[4/4] Restarting services...")
        run_cmd(ssh, "cd /opt/mycosoft/website && docker compose -f docker-compose.always-on.yml up -d mycosoft-website", sudo=True)
        
        # Check status
        print("\n" + "=" * 70)
        print("CONTAINER STATUS")
        print("=" * 70)
        run_cmd(ssh, "docker ps --format 'table {{.Names}}\\t{{.Status}}'", sudo=True)
        
        ssh.close()
        print(f"\n[OK] {name} deployment complete!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to deploy to {name}: {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("MYCA ORCHESTRATOR MEMORY INTEGRATION DEPLOYMENT")
    print("February 3, 2026")
    print("=" * 70)
    print()
    print("Features being deployed:")
    print("  - PromptManager (10k + 792 char prompts)")
    print("  - Memory API (5 scopes)")
    print("  - Voice Orchestrator API")
    print("  - Memory Summarization")
    print("  - PersonaPlex Bridge v4.0.0 (pure I/O)")
    print("  - Voice Session Manager with RTF tracking")
    print()
    
    # Deploy to Sandbox
    sandbox_ok = deploy_to_vm(SANDBOX_IP, "Sandbox VM")
    
    # Deploy to MAS VM
    mas_ok = deploy_to_vm(MAS_VM_IP, "MAS VM")
    
    print()
    print("=" * 70)
    print("DEPLOYMENT SUMMARY")
    print("=" * 70)
    print(f"  Sandbox VM ({SANDBOX_IP}): {'SUCCESS' if sandbox_ok else 'FAILED'}")
    print(f"  MAS VM ({MAS_VM_IP}):      {'SUCCESS' if mas_ok else 'FAILED'}")
    print()
    print("Next steps:")
    print("  1. Clear Cloudflare cache: https://dash.cloudflare.com")
    print("  2. Test: https://sandbox.mycosoft.com/test-voice")
    print("  3. Verify MAS health: http://192.168.0.188:8001/health")
