#!/usr/bin/env python3
"""Check VM containers vs local containers and fix issues"""

import paramiko

VM_IP = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASSWORD = "Mushroom1!Mushroom1!"

def run_sudo(ssh, cmd):
    full_cmd = f"echo '{VM_PASSWORD}' | sudo -S {cmd}"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=120)
    out = stdout.read().decode()
    err = stderr.read().decode()
    err_clean = "\n".join([l for l in err.split("\n") if "password" not in l.lower() and l.strip()])
    return out, err_clean

def main():
    print("="*60)
    print("CHECKING VM vs LOCAL CONTAINERS")
    print("="*60)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(VM_IP, username=VM_USER, password=VM_PASSWORD, timeout=30)
    print("Connected to VM!")
    
    # Check running containers on VM
    print("\n1. CONTAINERS ON VM:")
    print("-"*40)
    out, _ = run_sudo(ssh, "docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'")
    print(out)
    
    # Check loaded images on VM
    print("\n2. IMAGES ON VM:")
    print("-"*40)
    out, _ = run_sudo(ssh, "docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}' | grep -E 'mycosoft|mindex|website|REPOSITORY'")
    print(out)
    
    # Check website container specifically
    print("\n3. WEBSITE CONTAINER DETAILS:")
    print("-"*40)
    out, _ = run_sudo(ssh, "docker inspect mycosoft-website --format '{{.Config.Image}}' 2>/dev/null || echo 'Not found'")
    print(f"   Image: {out.strip()}")
    
    out, _ = run_sudo(ssh, "docker logs mycosoft-website --tail 20 2>&1 | tail -10")
    print(f"   Last logs:\n{out}")
    
    # Check MINDEX API
    print("\n4. MINDEX-API CONTAINER:")
    print("-"*40)
    out, _ = run_sudo(ssh, "docker inspect mindex-api --format '{{.Config.Image}}' 2>/dev/null || echo 'Not found'")
    print(f"   Image: {out.strip()}")
    
    out, _ = run_sudo(ssh, "docker logs mindex-api --tail 10 2>&1")
    print(f"   Last logs:\n{out[:500]}")
    
    # Check MycoBrain
    print("\n5. MYCOBRAIN CONTAINER:")
    print("-"*40)
    out, _ = run_sudo(ssh, "docker inspect mycobrain --format '{{.Config.Image}}' 2>/dev/null || echo 'Not found'")
    print(f"   Image: {out.strip()}")
    
    out, _ = run_sudo(ssh, "docker logs mycobrain --tail 10 2>&1")
    print(f"   Last logs:\n{out[:500]}")
    
    # Test website endpoint
    print("\n6. TESTING ENDPOINTS:")
    print("-"*40)
    endpoints = [
        ("Website root", "http://localhost:3000"),
        ("Website API health", "http://localhost:3000/api/health"),
        ("MINDEX API", "http://localhost:8000/api/mindex/health"),
        ("MycoBrain health", "http://localhost:8003/health"),
    ]
    
    for name, url in endpoints:
        stdin, stdout, stderr = ssh.exec_command(f"curl -s -o /dev/null -w '%{{http_code}}' {url} 2>/dev/null")
        code = stdout.read().decode().strip()
        print(f"   {name}: {code}")
    
    ssh.close()
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
