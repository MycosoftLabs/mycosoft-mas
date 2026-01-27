#!/usr/bin/env python3
"""Deploy updated orchestrator service to MAS VM"""

import paramiko
import time
from pathlib import Path

MAS_HOST = "192.168.0.188"
MAS_USER = "mycosoft"
MAS_PASS = "REDACTED_VM_SSH_PASSWORD"

def run_command(ssh, cmd, sudo=False):
    if sudo:
        cmd = f"echo '{MAS_PASS}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode(), stderr.read().decode()

def main():
    print(f"Deploying orchestrator update to {MAS_HOST}...")
    
    # Read the local orchestrator service file
    local_path = Path(__file__).parent.parent / "mycosoft_mas" / "core" / "orchestrator_service.py"
    print(f"Reading local file: {local_path}")
    
    with open(local_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"File size: {len(content)} bytes")
    
    # Connect to MAS VM
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(MAS_HOST, username=MAS_USER, password=MAS_PASS)
    print("Connected!")
    
    # Upload the file using SFTP
    sftp = ssh.open_sftp()
    
    # First, find where the orchestrator is running from
    out, _ = run_command(ssh, 'docker inspect myca-orchestrator --format "{{range .Mounts}}{{.Source}}:{{.Destination}} {{end}}"')
    print(f"Container mounts: {out}")
    
    # Check container working directory
    out, _ = run_command(ssh, 'docker inspect myca-orchestrator --format "{{.Config.WorkingDir}}"')
    print(f"Working dir: {out}")
    
    # Get the source code location
    out, _ = run_command(ssh, 'docker exec myca-orchestrator ls -la /app/core/ 2>/dev/null || echo "not found"')
    print(f"Container /app/core/: {out[:200]}")
    
    # Copy file to a temp location on VM
    remote_temp = "/tmp/orchestrator_service.py"
    print(f"Uploading to {remote_temp}...")
    
    with sftp.open(remote_temp, 'w') as f:
        f.write(content)
    print("Upload complete!")
    
    # Copy into the container
    print("Copying into container...")
    out, err = run_command(ssh, f'docker cp {remote_temp} myca-orchestrator:/app/core/orchestrator_service.py', sudo=True)
    if err and "password" not in err.lower():
        print(f"Copy error: {err}")
    print(f"Copy output: {out}")
    
    # Restart the container
    print("Restarting container...")
    out, err = run_command(ssh, 'docker restart myca-orchestrator', sudo=True)
    print(f"Restart: {out}")
    
    # Wait for it to come up
    print("Waiting 15 seconds for container to start...")
    time.sleep(15)
    
    # Test the new endpoint
    print("\n=== Testing voice chat endpoint ===")
    out, _ = run_command(ssh, 'curl -s -X POST http://localhost:8001/voice/orchestrator/chat -H "Content-Type: application/json" -d \'{"message":"hello"}\'')
    print(f"Response: {out}")
    
    sftp.close()
    ssh.close()
    print("\n=== Done ===")

if __name__ == "__main__":
    main()
