#!/usr/bin/env python3
"""
Full Mycosoft System Deployment to VM 103
Following docs/COMPLETE_VM_DEPLOYMENT_GUIDE.md
"""
import paramiko
import os
import time

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"

# Local paths on Windows
MAS_PATH = r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\MAS\mycosoft-mas"
WEBSITE_PATH = r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website"

def run_cmd(ssh, cmd, sudo=False, timeout=300):
    """Run command on VM"""
    if sudo:
        cmd = f"echo '{VM_PASS}' | sudo -S {cmd}"
    print(f">>> {cmd[:80]}...")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        lines = out.strip().split('\n')
        if len(lines) > 10:
            print('\n'.join(lines[-10:]))
        else:
            print(out)
    return out, err

def main():
    print("=" * 70)
    print("FULL MYCOSOFT SYSTEM DEPLOYMENT")
    print(f"Target: {VM_IP}")
    print("=" * 70)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASS)
    print("Connected!")
    
    # Step 1: Create directory structure
    print("\n" + "=" * 50)
    print("STEP 1: Creating directory structure")
    print("=" * 50)
    
    dirs = [
        "/opt/mycosoft",
        "/opt/mycosoft/mas",
        "/opt/mycosoft/website", 
        "/opt/mycosoft/data/postgres",
        "/opt/mycosoft/data/redis",
        "/opt/mycosoft/data/qdrant",
        "/opt/mycosoft/data/n8n",
        "/opt/mycosoft/data/mindex",
        "/opt/mycosoft/backups",
        "/opt/mycosoft/logs",
        "/opt/mycosoft/config"
    ]
    
    for d in dirs:
        run_cmd(ssh, f"mkdir -p {d}", sudo=True)
    
    run_cmd(ssh, f"chown -R {VM_USER}:{VM_USER} /opt/mycosoft", sudo=True)
    
    # Step 2: Create Docker networks
    print("\n" + "=" * 50)
    print("STEP 2: Creating Docker networks")
    print("=" * 50)
    
    run_cmd(ssh, "docker network create mycosoft-always-on 2>/dev/null || true", sudo=True)
    run_cmd(ssh, "docker network create mycosoft-mas_mas-network 2>/dev/null || true", sudo=True)
    run_cmd(ssh, "docker network ls | grep mycosoft", sudo=True)
    
    # Step 3: Check what we need to transfer
    print("\n" + "=" * 50)
    print("STEP 3: Checking repository status")
    print("=" * 50)
    
    # Check if git is available and repos can be cloned
    run_cmd(ssh, "which git")
    
    # For now, we'll need to use SCP to transfer files
    print("\nTo complete deployment, run these commands from Windows PowerShell:")
    print("-" * 60)
    print(f'''
# Transfer MAS repository:
scp -r "{MAS_PATH}\\*" mycosoft@{VM_IP}:/opt/mycosoft/mas/

# Transfer Website repository:
scp -r "{WEBSITE_PATH}\\*" mycosoft@{VM_IP}:/opt/mycosoft/website/

# Or use rsync (faster for large transfers):
# rsync -avz --progress "{MAS_PATH}/" mycosoft@{VM_IP}:/opt/mycosoft/mas/
# rsync -avz --progress "{WEBSITE_PATH}/" mycosoft@{VM_IP}:/opt/mycosoft/website/
''')
    
    ssh.close()
    print("\n" + "=" * 70)
    print("DIRECTORY STRUCTURE READY")
    print("Next: Transfer codebases, then run deployment")
    print("=" * 70)

if __name__ == "__main__":
    main()
