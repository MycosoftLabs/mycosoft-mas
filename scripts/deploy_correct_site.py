#!/usr/bin/env python3
"""Deploy the correct website image to VM 103."""

import paramiko
from scp import SCPClient
import time

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"
IMAGE_FILE = r"C:\temp\correct-website.tar"

def create_ssh_client():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS)
    return ssh

def run_sudo(ssh, command):
    """Run a command with sudo."""
    full_cmd = f"echo {VM_PASS} | sudo -S {command}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd)
    return stdout.read().decode(), stderr.read().decode()

def main():
    print("=" * 60)
    print("DEPLOYING CORRECT WEBSITE TO VM 103")
    print("=" * 60)
    
    ssh = create_ssh_client()
    
    # Step 1: Transfer the image
    print("\n[1/5] Transferring image to VM (98 MB)...")
    scp = SCPClient(ssh.get_transport())
    scp.put(IMAGE_FILE, "/tmp/correct-website.tar")
    scp.close()
    print("  Transfer complete!")
    
    # Step 2: Load the image
    print("\n[2/5] Loading Docker image...")
    out, err = run_sudo(ssh, "docker load -i /tmp/correct-website.tar")
    print(f"  {out.strip()}")
    
    # Step 3: Stop current website container
    print("\n[3/5] Stopping current website container...")
    out, err = run_sudo(ssh, "docker stop mycosoft-website 2>/dev/null || true")
    out, err = run_sudo(ssh, "docker rm mycosoft-website 2>/dev/null || true")
    print("  Stopped and removed old container")
    
    # Step 4: Start new container with correct image
    print("\n[4/5] Starting new container with correct image...")
    docker_run = """docker run -d \\
        --name mycosoft-website \\
        --restart unless-stopped \\
        -p 3000:3000 \\
        -e NODE_ENV=production \\
        -e NEXT_PUBLIC_MINDEX_URL=http://mindex-api:8000 \\
        -e NEXT_PUBLIC_MYCOBRAIN_URL=http://mycobrain:8003 \\
        --network mycosoft-always-on \\
        website-website:latest"""
    out, err = run_sudo(ssh, docker_run)
    if err and "Error" in err:
        print(f"  Error: {err}")
    else:
        print(f"  Container ID: {out.strip()[:12]}")
    
    # Step 5: Verify
    print("\n[5/5] Verifying deployment...")
    time.sleep(3)
    stdin, stdout, stderr = ssh.exec_command("docker ps --filter name=mycosoft-website --format '{{.Names}}: {{.Status}}'")
    status = stdout.read().decode().strip()
    print(f"  {status}")
    
    # Test the endpoint
    stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
    code = stdout.read().decode().strip()
    print(f"  HTTP Response: {code}")
    
    # Clean up
    print("\n[Cleanup] Removing temp file...")
    run_sudo(ssh, "rm /tmp/correct-website.tar")
    
    ssh.close()
    
    print("\n" + "=" * 60)
    print("DEPLOYMENT COMPLETE!")
    print("=" * 60)
    print("\nPlease refresh https://sandbox.mycosoft.com/ in an incognito window")

if __name__ == "__main__":
    main()
