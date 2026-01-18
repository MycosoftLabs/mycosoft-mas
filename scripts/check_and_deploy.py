#!/usr/bin/env python3
"""
Check VM status, deploy website, and test
"""
import requests
import urllib3
import paramiko
import time
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.stdout.reconfigure(encoding='utf-8')

# Proxmox config
PROXMOX_HOST = "https://192.168.0.202:8006"
PROXMOX_TOKEN_ID = "myca@pve!mas"
PROXMOX_TOKEN_SECRET = "ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"
VM_ID = 103
NODE = "pve"

# SSH config
VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

headers = {
    "Authorization": f"PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}"
}

def check_vm_proxmox():
    """Check VM status via Proxmox API"""
    print("=" * 60)
    print("  CHECKING VM 103 STATUS")
    print("=" * 60)
    
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/status/current"
    try:
        resp = requests.get(url, headers=headers, verify=False, timeout=10)
        if resp.ok:
            data = resp.json().get("data", {})
            print(f"  Name: {data.get('name')}")
            print(f"  Status: {data.get('status')}")
            print(f"  Memory: {data.get('maxmem', 0) // (1024**3)}GB")
            print(f"  CPUs: {data.get('cpus')}")
            return data.get("status") == "running"
    except Exception as e:
        print(f"  Error: {e}")
    return False

def deploy_via_ssh():
    """Deploy website via SSH"""
    print("\n" + "=" * 60)
    print("  DEPLOYING WEBSITE VIA SSH")
    print("=" * 60)
    
    print(f"\nConnecting to {VM_HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
    except Exception as e:
        print(f"  Connection failed: {e}")
        return False
    
    print("Connected!\n")
    
    def run_cmd(cmd, timeout=300):
        """Run command and print output"""
        _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8', errors='replace')
        err = stderr.read().decode('utf-8', errors='replace')
        return exit_code, out, err
    
    # Check disk space
    print("[1] Checking disk space...")
    _, out, _ = run_cmd("df -h /")
    print(out)
    
    # Check memory
    print("[2] Checking memory...")
    _, out, _ = run_cmd("free -h")
    print(out)
    
    # Pull latest code
    print("[3] Pulling latest code from GitHub...")
    exit_code, out, err = run_cmd("cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main 2>&1")
    print(out[-500:] if len(out) > 500 else out)
    
    # Check Docker
    print("[4] Checking Docker containers...")
    _, out, _ = run_cmd("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
    print(out)
    
    # Build new image
    print("[5] Building Docker image (this takes 3-5 minutes)...")
    build_cmd = f"cd /opt/mycosoft/website && echo '{VM_PASS}' | sudo -S docker build -t website-website:latest --no-cache . 2>&1"
    exit_code, out, err = run_cmd(build_cmd, timeout=600)
    
    # Show last 50 lines
    lines = out.strip().split('\n')
    print('\n'.join(lines[-50:]))
    print(f"\nBuild exit code: {exit_code}")
    
    if exit_code != 0:
        print("\n!!! BUILD FAILED !!!")
        ssh.close()
        return False
    
    # Stop old container
    print("\n[6] Stopping old container...")
    run_cmd(f"echo '{VM_PASS}' | sudo -S docker stop mycosoft-website 2>/dev/null || true")
    run_cmd(f"echo '{VM_PASS}' | sudo -S docker rm mycosoft-website 2>/dev/null || true")
    print("Done")
    
    # Start new container
    print("\n[7] Starting new container...")
    _, out, _ = run_cmd(f"cd /opt/mycosoft && echo '{VM_PASS}' | sudo -S docker compose -p mycosoft-production up -d mycosoft-website 2>&1")
    print(out)
    
    # Wait for startup
    print("\n[8] Waiting 20 seconds for startup...")
    time.sleep(20)
    
    # Check container status
    print("\n[9] Container status:")
    _, out, _ = run_cmd("docker ps --filter name=mycosoft-website --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
    print(out)
    
    # Test health
    print("\n[10] Testing localhost:3000...")
    _, out, _ = run_cmd("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
    print(f"HTTP Status: {out.strip()}")
    
    # Test login page
    print("\n[11] Testing login page...")
    _, out, _ = run_cmd("curl -s http://localhost:3000/login | grep -o 'Sign in with' | head -1")
    print(f"Login page check: {out.strip() if out.strip() else 'Page loaded'}")
    
    ssh.close()
    return True

def test_external():
    """Test external access"""
    print("\n" + "=" * 60)
    print("  TESTING EXTERNAL ACCESS")
    print("=" * 60)
    
    import subprocess
    
    # Test sandbox.mycosoft.com
    print("\nTesting https://sandbox.mycosoft.com...")
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "NUL", "-w", "%{http_code}", "https://sandbox.mycosoft.com"],
            capture_output=True, text=True, timeout=30
        )
        print(f"  HTTP Status: {result.stdout}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Test login page
    print("\nTesting https://sandbox.mycosoft.com/login...")
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "NUL", "-w", "%{http_code}", "https://sandbox.mycosoft.com/login"],
            capture_output=True, text=True, timeout=30
        )
        print(f"  HTTP Status: {result.stdout}")
    except Exception as e:
        print(f"  Error: {e}")

def main():
    # Check VM
    if not check_vm_proxmox():
        print("\nVM is not running! Starting VM...")
        url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/status/start"
        resp = requests.post(url, headers=headers, verify=False)
        if resp.ok:
            print("VM start initiated, waiting 60 seconds...")
            time.sleep(60)
        else:
            print(f"Failed to start VM: {resp.text}")
            return 1
    
    # Deploy
    if not deploy_via_ssh():
        print("\nDeployment failed!")
        return 1
    
    # Test external
    test_external()
    
    print("\n" + "=" * 60)
    print("  ALL DONE!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Clear Cloudflare cache (PURGE EVERYTHING)")
    print("2. Test: https://sandbox.mycosoft.com/login?redirectTo=%2Fdashboard%2Fcrep")
    print("3. Click Google/GitHub login and verify redirect works")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
