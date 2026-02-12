#!/usr/bin/env python3
"""Rebuild MAS Docker image on VM with latest code"""
import os
import sys
import time
import paramiko

MAS_VM_IP = "192.168.0.188"
MAS_VM_USER = "mycosoft"
MAS_VM_PASS = os.environ.get("VM_PASSWORD", "Mushroom1!Mushroom1!")

def run_sudo(ssh, cmd, password, show_output=True):
    """Execute command with sudo"""
    full_cmd = f"echo '{password}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=600, get_pty=True)
    
    if show_output:
        while True:
            line = stdout.readline()
            if not line:
                break
            if 'password' not in line.lower():
                print(f"    {line.rstrip()}")
    else:
        output = stdout.read().decode('utf-8', errors='ignore')
    
    return stdout.channel.recv_exit_status() == 0

def main():
    print("=" * 70)
    print("REBUILD MAS DOCKER IMAGE WITH LATEST CODE")
    print("=" * 70)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"[*] Connecting to {MAS_VM_IP}...")
    ssh.connect(MAS_VM_IP, username=MAS_VM_USER, password=MAS_VM_PASS, timeout=30)
    print("[+] Connected\n")
    
    # Show current commit
    print("[*] Current commit on VM:")
    stdin, stdout, stderr = ssh.exec_command("cd ~/mycosoft/mas && git log -1 --oneline")
    print(f"    {stdout.read().decode().strip()}\n")
    
    # Stop container
    print("[*] Stopping existing container...")
    run_sudo(ssh, "docker stop myca-orchestrator-new 2>&1", MAS_VM_PASS, show_output=False)
    run_sudo(ssh, "docker rm myca-orchestrator-new 2>&1", MAS_VM_PASS, show_output=False)
    print("[+] Container stopped\n")
    
    # Rebuild Docker image
    print("[*] Building new Docker image (this will take a few minutes)...")
    success = run_sudo(ssh, 
        "cd /home/mycosoft/mycosoft/mas && docker build -t mycosoft/mas-agent:latest --no-cache .",
        MAS_VM_PASS, show_output=True)
    
    if success:
        print("\n[+] Docker image built successfully\n")
    else:
        print("\n[!] Build may have had issues\n")
    
    # Start new container
    print("[*] Starting new container with updated image...")
    cmd = """docker run -d \\
        --name myca-orchestrator-new \\
        --restart unless-stopped \\
        -p 8001:8000 \\
        --env-file /home/mycosoft/mycosoft/mas/.env \\
        mycosoft/mas-agent:latest"""
    
    run_sudo(ssh, cmd, MAS_VM_PASS, show_output=False)
    print("[+] Container started\n")
    
    # Wait for startup
    print("[*] Waiting 15 seconds for container to become healthy...")
    time.sleep(15)
    
    # Check status
    print("[*] Container status:")
    stdin, stdout, stderr = ssh.exec_command("docker ps --filter name=myca-orchestrator")
    for line in stdout.read().decode().split('\n'):
        if line.strip():
            print(f"    {line}")
    
    ssh.close()
    
    print("\n" + "=" * 70)
    print("REBUILD COMPLETE - Testing API...")
    print("=" * 70)
    
    time.sleep(5)
    
    # Test API
    import urllib.request
    import json
    
    try:
        with urllib.request.urlopen(f"http://{MAS_VM_IP}:8001/health", timeout=15) as resp:
            data = json.loads(resp.read().decode())
            print(f"[+] API Status: {data.get('status')}\n")
    except Exception as e:
        print(f"[!] API test: {e}\n")
    
    print("Test MYCA with corrected intent engine:")
    print(f"""
  curl -X POST http://{MAS_VM_IP}:8001/api/myca/route \\
    -H "Content-Type: application/json" \\
    -d '{{"message": "Tell me about Amanita muscaria"}}'

Should now show intent_confidence: 0.95 (LLM) instead of 0.6 (rules)
""")

if __name__ == "__main__":
    main()
