#!/usr/bin/env python3
"""Transfer correct website image to VM and redeploy"""

import paramiko
from scp import SCPClient
from pathlib import Path
import time

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"

EXPORT_DIR = Path(r"C:\Users\admin2\Desktop\MYCOSOFT\DOCKER_EXPORTS")

def run_sudo(ssh, cmd):
    """Run command with sudo"""
    full_cmd = f"echo '{VM_PASSWORD}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=300)
    out = stdout.read().decode()
    err = stderr.read().decode()
    # Filter password noise
    err_clean = "\n".join([l for l in err.split("\n") if "password" not in l.lower() and l.strip()])
    return out, err_clean

def main():
    print("=" * 60)
    print("FIXING WEBSITE IMAGE ON VM")
    print("=" * 60)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
    print("Connected to VM!")
    
    # Transfer the correct website image
    print("\n1. Transferring correct website image...")
    tar_file = EXPORT_DIR / "mycosoft-always-on-mycosoft-website_latest.tar"
    
    def progress(filename, size, sent):
        pct = (sent / size) * 100
        bar = "=" * int(pct/5) + ">" + " " * (20 - int(pct/5))
        print(f"\r[{bar}] {pct:.1f}%", end="", flush=True)
    
    scp = SCPClient(ssh.get_transport(), progress=progress)
    scp.put(str(tar_file), "/opt/mycosoft/images/mycosoft-always-on-mycosoft-website_latest.tar")
    scp.close()
    print(" DONE")
    
    # Load the image
    print("\n2. Loading the correct website image...")
    out, err = run_sudo(ssh, "docker load -i /opt/mycosoft/images/mycosoft-always-on-mycosoft-website_latest.tar")
    print(f"   {out}")
    if err:
        print(f"   Error: {err}")
    
    # Stop the current website container
    print("\n3. Stopping current website container...")
    out, err = run_sudo(ssh, "docker stop mycosoft-website")
    print(f"   {out}")
    
    out, err = run_sudo(ssh, "docker rm mycosoft-website")
    print(f"   {out}")
    
    # Update docker-compose to use correct image
    print("\n4. Updating docker-compose.yml...")
    compose_update = '''
# Update the website image in docker-compose.yml
sed -i 's/website-website:latest/mycosoft-always-on-mycosoft-website:latest/g' /opt/mycosoft/docker-compose.yml
'''
    out, err = run_sudo(ssh, "sed -i 's/website-website:latest/mycosoft-always-on-mycosoft-website:latest/g' /opt/mycosoft/docker-compose.yml")
    print(f"   Updated image name")
    
    # Start the website with new image
    print("\n5. Starting website with correct image...")
    out, err = run_sudo(ssh, "sh -c 'cd /opt/mycosoft && docker compose up -d mycosoft-website'")
    print(f"   {out}")
    if err:
        print(f"   {err}")
    
    # Wait and check
    print("\n6. Waiting 20 seconds for website to start...")
    time.sleep(20)
    
    # Verify
    print("\n7. Verifying website...")
    out, err = run_sudo(ssh, "docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | grep website")
    print(f"   {out}")
    
    # Test endpoint
    stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
    code = stdout.read().decode().strip()
    print(f"   HTTP Status: {code}")
    
    ssh.close()
    
    print("\n" + "=" * 60)
    print("WEBSITE FIX COMPLETE!")
    print("=" * 60)

if __name__ == "__main__":
    main()
