#!/usr/bin/env python3
"""Compare Docker images"""

import paramiko
import subprocess

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"

def main():
    # Local images
    print("=== LOCAL DOCKER IMAGES (website) ===")
    result = subprocess.run(
        ["docker", "images", "--format", "{{.Repository}}:{{.Tag}} - {{.ID}}"],
        capture_output=True, text=True
    )
    for line in result.stdout.split("\n"):
        if "website" in line.lower():
            print(f"  {line}")

    # VM images
    print("\n=== VM DOCKER IMAGES (website) ===")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
    
    cmd = f"echo '{VM_PASSWORD}' | sudo -S docker images --format '{{{{.Repository}}}}:{{{{.Tag}}}} - {{{{.ID}}}}'"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    for line in out.split("\n"):
        if "website" in line.lower():
            print(f"  {line}")
    
    # Check which image the container is using
    print("\n=== RUNNING WEBSITE CONTAINER ===")
    cmd = f"echo '{VM_PASSWORD}' | sudo -S docker inspect mycosoft-website --format '{{{{.Image}}}}'"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    image_id = stdout.read().decode().strip()
    print(f"  Container image ID: {image_id}")
    
    # Check if this matches the correct always-on image
    cmd = f"echo '{VM_PASSWORD}' | sudo -S docker images mycosoft-always-on-mycosoft-website --format '{{{{.ID}}}}'"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    correct_id = stdout.read().decode().strip()
    print(f"  Correct always-on image ID: {correct_id}")
    
    if image_id.startswith("sha256:" + correct_id) or correct_id in image_id:
        print("  MATCH!")
    else:
        print("  MISMATCH - container is using wrong image!")
    
    ssh.close()

if __name__ == "__main__":
    main()
