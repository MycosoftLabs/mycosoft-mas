"""
Deploy optimized MYCA consciousness pipeline to MAS VM.

Author: Morgan Rockwell / MYCA
Date: February 11, 2026
"""

import paramiko
import sys
import time
from pathlib import Path

# VM Configuration
MAS_VM_IP = "192.168.0.188"
MAS_VM_USER = "mycosoft"
MAS_VM_PASSWORD = "Mushroom1!Mushroom1!"
MAS_REPO_PATH = "/home/mycosoft/mycosoft/mas"

def ssh_execute(ssh_client, command: str, timeout: int = 60):
    """Execute a command via SSH and return output."""
    print(f"\n[CMD] {command}")
    stdin, stdout, stderr = ssh_client.exec_command(command, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')
    
    if output:
        print(output)
    if error:
        print(f"[ERROR] {error}", file=sys.stderr)
    
    return exit_code, output, error

def deploy_mas():
    """Deploy optimized consciousness to MAS VM."""
    print("=" * 80)
    print("DEPLOYING OPTIMIZED MYCA CONSCIOUSNESS PIPELINE")
    print("=" * 80)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Connect
        print(f"\n[1/6] Connecting to MAS VM ({MAS_VM_IP})...")
        ssh.connect(MAS_VM_IP, username=MAS_VM_USER, password=MAS_VM_PASSWORD)
        print("[OK] Connected")
        
        # Pull latest code
        print("\n[2/6] Pulling latest code...")
        code, out, err = ssh_execute(ssh, f"cd {MAS_REPO_PATH} && git pull origin main")
        if code != 0:
            print("[FAIL] Git pull failed")
            return False
        print("[OK] Code updated")
        
        # Rebuild Docker image
        print("\n[3/6] Rebuilding Docker image (this may take 2-3 minutes)...")
        code, out, err = ssh_execute(
            ssh,
            f"cd {MAS_REPO_PATH} && echo '{MAS_VM_PASSWORD}' | sudo -S docker build -t mycosoft/mas-agent:latest --no-cache .",
            timeout=300
        )
        if code != 0:
            print("[FAIL] Docker build failed")
            return False
        print("[OK] Image built")
        
        # Stop old container
        print("\n[4/6] Stopping old container...")
        ssh_execute(ssh, f"echo '{MAS_VM_PASSWORD}' | sudo -S docker stop myca-orchestrator-new")
        ssh_execute(ssh, f"echo '{MAS_VM_PASSWORD}' | sudo -S docker rm myca-orchestrator-new")
        print("[OK] Old container stopped")
        
        # Start new container
        print("\n[5/6] Starting new container...")
        code, out, err = ssh_execute(
            ssh,
            f"echo '{MAS_VM_PASSWORD}' | sudo -S docker run -d --name myca-orchestrator-new "
            "--restart unless-stopped "
            "-p 8001:8000 "
            "mycosoft/mas-agent:latest"
        )
        if code != 0:
            print("[FAIL] Container start failed")
            return False
        print("[OK] Container started")
        
        # Wait for startup
        print("\n[6/6] Waiting for startup...")
        time.sleep(10)
        
        # Check health
        code, out, err = ssh_execute(
            ssh,
            "curl -s http://localhost:8001/health || echo 'FAILED'"
        )
        if "healthy" in out.lower():
            print("[OK] MAS is healthy")
            print("\n" + "=" * 80)
            print("DEPLOYMENT SUCCESSFUL")
            print("=" * 80)
            print("\nMAS API: http://192.168.0.188:8001")
            print("Test consciousness: python scripts/test_three_questions.py")
            return True
        else:
            print("[FAIL] Health check failed")
            return False
        
    except Exception as e:
        print(f"\n[FAIL] Deployment failed: {e}")
        return False
    
    finally:
        ssh.close()

if __name__ == "__main__":
    success = deploy_mas()
    sys.exit(0 if success else 1)
