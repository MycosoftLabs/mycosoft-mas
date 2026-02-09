#!/usr/bin/env python3
"""
VM Recovery - Restart Docker, cleanup, and deploy - Feb 6, 2026
Full automated recovery with sudo access
"""
import paramiko
import time
import requests

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"

def run_sudo(ssh, cmd, timeout=120):
    """Run command with sudo, providing password via stdin"""
    full_cmd = f'echo {VM_PASS} | sudo -S {cmd}'
    print(f"[SUDO] {cmd}")
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=timeout)
    try:
        stdout.channel.settimeout(timeout)
        out = stdout.read().decode()
        if out:
            print(f"  {out[:200]}")
        return out
    except Exception as e:
        print(f"  (timeout/error: {e})")
        return ""

def run(ssh, cmd, timeout=60):
    """Run command normally"""
    print(f"[CMD] {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    try:
        stdout.channel.settimeout(timeout)
        out = stdout.read().decode()
        if out:
            print(f"  {out[:300]}")
        return out
    except Exception as e:
        print(f"  (timeout/error: {e})")
        return ""

def main():
    print("="*60)
    print("VM RECOVERY - Full Docker Restart & Cleanup")
    print("="*60)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"\nConnecting to {VM_IP}...")
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS, timeout=30)
    print("Connected!\n")
    
    # Step 1: Check current memory
    print("="*60)
    print("Step 1: Current Memory Status")
    print("="*60)
    run(ssh, "free -h", timeout=10)
    
    # Step 2: Restart Docker daemon with sudo
    print("\n" + "="*60)
    print("Step 2: Restarting Docker Daemon")
    print("="*60)
    run_sudo(ssh, "systemctl restart docker", timeout=60)
    print("Waiting 15 seconds for Docker to restart...")
    time.sleep(15)
    
    # Step 3: Aggressive Docker cleanup
    print("\n" + "="*60)
    print("Step 3: Docker Cleanup (prune everything)")
    print("="*60)
    run(ssh, "docker container prune -f", timeout=120)
    run(ssh, "docker image prune -a -f", timeout=180)
    run(ssh, "docker volume prune -f", timeout=60)
    run(ssh, "docker builder prune -a -f", timeout=120)
    run(ssh, "docker system prune -a -f --volumes", timeout=180)
    
    # Step 4: Check memory after cleanup
    print("\n" + "="*60)
    print("Step 4: Memory After Cleanup")
    print("="*60)
    run(ssh, "free -h", timeout=10)
    
    # Step 5: Pull latest code and start website
    print("\n" + "="*60)
    print("Step 5: Pull Latest Code & Start Website")
    print("="*60)
    run(ssh, "cd /home/mycosoft/mycosoft/mas && git fetch origin && git reset --hard origin/main", timeout=60)
    run(ssh, "cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml up -d mycosoft-website", timeout=300)
    
    # Step 6: Wait for startup
    print("\n" + "="*60)
    print("Step 6: Waiting for Website Container (90 seconds)...")
    print("="*60)
    ssh.close()
    
    for i in range(9):
        time.sleep(10)
        print(f"  {(i+1)*10}s...")
    
    # Step 7: Test endpoint
    print("\n" + "="*60)
    print("Step 7: Testing Endpoints")
    print("="*60)
    
    try:
        r = requests.get('https://sandbox.mycosoft.com/api/mycobrain/health', timeout=30)
        print(f"Sandbox MycoBrain: {r.status_code}")
        if r.status_code == 200:
            print(f"SUCCESS! Response: {r.json()}")
        else:
            print(f"Response: {r.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")
    
    try:
        r = requests.get('https://sandbox.mycosoft.com/', timeout=30)
        print(f"Sandbox Homepage: {r.status_code}")
    except Exception as e:
        print(f"Homepage error: {e}")
    
    print("\n" + "="*60)
    print("RECOVERY COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()
