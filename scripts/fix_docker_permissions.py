#!/usr/bin/env python3
"""Fix Docker permissions and start services on VM"""

import paramiko
import time

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "REDACTED_VM_SSH_PASSWORD"

def run_sudo_cmd(ssh, cmd):
    """Run a command with sudo using -S flag"""
    full_cmd = f"echo '{VM_PASSWORD}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=300)
    out = stdout.read().decode()
    err = stderr.read().decode()
    # Filter out password prompt noise
    err_clean = "\n".join([l for l in err.split("\n") if "password" not in l.lower() and l.strip()])
    return out, err_clean

def main():
    print("Connecting to VM...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
    print("Connected!")
    
    # Add user to docker group
    print("\n1. Adding user to docker group...")
    out, err = run_sudo_cmd(ssh, "usermod -aG docker mycosoft")
    print(f"   {out}{err}")
    
    # Load Docker images
    print("\n2. Loading Docker images from tar files...")
    out, err = run_sudo_cmd(ssh, "cd /opt/mycosoft/images && ls -la")
    print(f"   Files: {out}")
    
    for tar_file in ["website-website_latest.tar", "mycosoft-always-on-mindex-api_latest.tar", 
                     "mycosoft-always-on-mindex-etl_latest.tar", "mycosoft-always-on-mycobrain_latest.tar",
                     "mycosoft-mas-mas-orchestrator_latest.tar", "mycosoft-mas-unifi-dashboard_latest.tar"]:
        print(f"   Loading {tar_file}...")
        out, err = run_sudo_cmd(ssh, f"docker load -i /opt/mycosoft/images/{tar_file}")
        if "Loaded image" in out:
            print(f"   -> {out.strip()}")
        elif err:
            print(f"   -> Error: {err[:100]}")
    
    # List loaded images
    print("\n3. Loaded images:")
    out, err = run_sudo_cmd(ssh, "docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}'")
    print(out)
    
    # Start docker compose
    print("\n4. Starting docker compose...")
    out, err = run_sudo_cmd(ssh, "cd /opt/mycosoft && docker compose up -d")
    print(f"   {out}")
    if err:
        print(f"   Errors: {err}")
    
    # Wait for services
    print("\n5. Waiting 30 seconds for services to start...")
    time.sleep(30)
    
    # Check running containers
    print("\n6. Running containers:")
    out, err = run_sudo_cmd(ssh, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
    print(out)
    
    # Test endpoints
    print("\n7. Testing endpoints:")
    endpoints = [
        ("Website", "http://localhost:3000"),
        ("MINDEX", "http://localhost:8000/api/mindex/health"),
        ("MycoBrain", "http://localhost:8003/health"),
        ("n8n", "http://localhost:5678"),
    ]
    
    for name, url in endpoints:
        stdin, stdout, stderr = ssh.exec_command(f"curl -s -o /dev/null -w '%{{http_code}}' {url} 2>/dev/null || echo 'FAIL'")
        code = stdout.read().decode().strip()
        status = "OK" if code in ["200", "301", "302"] else code
        print(f"   {name}: {status}")
    
    ssh.close()
    print("\nDone!")

if __name__ == "__main__":
    main()
