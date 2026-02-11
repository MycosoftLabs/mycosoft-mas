#!/usr/bin/env python3
"""
Restart MAS container on VM to pick up new environment variables
"""
import os
import sys
import time

try:
    import paramiko
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko", "-q"])
    import paramiko

MAS_VM_IP = "192.168.0.188"
MAS_VM_USER = "mycosoft"
MAS_VM_PASS = os.environ.get("VM_PASSWORD", "REDACTED_VM_SSH_PASSWORD")

def run_sudo(ssh, cmd, password):
    """Execute command with sudo"""
    full_cmd = f"echo '{password}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=120, get_pty=True)
    output = stdout.read().decode('utf-8', errors='ignore')
    return output

def main():
    print("=" * 60)
    print("RESTARTING MAS CONTAINER")
    print("=" * 60)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"[*] Connecting to {MAS_VM_IP}...")
    ssh.connect(MAS_VM_IP, username=MAS_VM_USER, password=MAS_VM_PASS, timeout=30)
    print("[+] Connected")
    
    # Stop container
    print("[*] Stopping MAS container...")
    output = run_sudo(ssh, "docker stop myca-orchestrator-new 2>&1 || docker stop myca-orchestrator 2>&1", MAS_VM_PASS)
    print("    Container stopped")
    
    # Remove container
    print("[*] Removing container...")
    output = run_sudo(ssh, "docker rm myca-orchestrator-new 2>&1 || docker rm myca-orchestrator 2>&1", MAS_VM_PASS)
    print("    Container removed")
    
    # Start new container with env file
    print("[*] Starting new container with updated environment...")
    cmd = """docker run -d \\
        --name myca-orchestrator-new \\
        --restart unless-stopped \\
        -p 8001:8000 \\
        --env-file /home/mycosoft/mycosoft/mas/.env \\
        mycosoft/mas-agent:latest 2>&1"""
    
    output = run_sudo(ssh, cmd, MAS_VM_PASS)
    print(f"    {output.strip()}")
    
    # Wait for startup
    print("[*] Waiting for container to start...")
    time.sleep(10)
    
    # Check status
    print("[*] Checking container status...")
    stdin, stdout, stderr = ssh.exec_command("docker ps --filter name=myca-orchestrator")
    output = stdout.read().decode()
    for line in output.split('\n')[1:]:  # Skip header
        if line.strip():
            print(f"    {line.strip()}")
    
    ssh.close()
    
    print("\n[+] Container restarted successfully")
    print(f"[*] Testing API in 5 seconds...")
    time.sleep(5)
    
    # Test API
    import urllib.request
    import json
    
    try:
        with urllib.request.urlopen(f"http://{MAS_VM_IP}:8001/health", timeout=15) as resp:
            data = json.loads(resp.read().decode())
            print(f"[+] API responding: {data.get('status')}")
    except Exception as e:
        print(f"[!] API test: {e}")
    
    print("\n" + "=" * 60)
    print("Test MYCA now:")
    print(f"""
  curl -X POST http://{MAS_VM_IP}:8001/api/myca/route \\
    -H "Content-Type: application/json" \\
    -d '{{"message": "Are you alive and well?"}}'
""")

if __name__ == "__main__":
    main()
