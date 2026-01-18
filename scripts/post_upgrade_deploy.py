#!/usr/bin/env python3
"""
Post-upgrade: Expand LVM, deploy website, test everything
"""
import paramiko
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

def run_cmd(ssh, cmd, timeout=300, show_all=False):
    """Execute command and return output"""
    print(f">>> {cmd[:80]}...")
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    
    if show_all or len(out) < 2000:
        print(out)
    else:
        lines = out.strip().split('\n')
        print('\n'.join(lines[-30:]))
    
    if err and exit_code != 0:
        print(f"STDERR: {err[:500]}")
    
    return exit_code, out

def main():
    print("=" * 60)
    print("  POST-UPGRADE: EXPAND LVM + DEPLOY + TEST")
    print("=" * 60)
    
    # Wait for VM to be fully ready
    print("\nWaiting 20s for VM services to initialize...")
    time.sleep(20)
    
    print(f"\nConnecting to {VM_HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    for attempt in range(3):
        try:
            ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
            print("Connected!")
            break
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            if attempt < 2:
                time.sleep(10)
            else:
                print("Could not connect to VM")
                return 1
    
    # Step 1: Check current disk space
    print("\n" + "=" * 40)
    print("[1] CURRENT DISK SPACE")
    print("=" * 40)
    run_cmd(ssh, "df -h /", show_all=True)
    run_cmd(ssh, "lsblk", show_all=True)
    
    # Step 2: Expand LVM partition
    print("\n" + "=" * 40)
    print("[2] EXPANDING LVM PARTITION")
    print("=" * 40)
    
    # Detect the physical volume and expand it
    print("\nScanning for new disk space...")
    run_cmd(ssh, f"echo '{VM_PASS}' | sudo -S growpart /dev/sda 3 2>&1 || echo 'Already expanded or not needed'", show_all=True)
    
    print("\nResizing physical volume...")
    run_cmd(ssh, f"echo '{VM_PASS}' | sudo -S pvresize /dev/sda3 2>&1", show_all=True)
    
    print("\nExtending logical volume to use all free space...")
    run_cmd(ssh, f"echo '{VM_PASS}' | sudo -S lvextend -l +100%FREE /dev/ubuntu-vg/ubuntu-lv 2>&1", show_all=True)
    
    print("\nResizing filesystem...")
    run_cmd(ssh, f"echo '{VM_PASS}' | sudo -S resize2fs /dev/ubuntu-vg/ubuntu-lv 2>&1", show_all=True)
    
    print("\nVerifying new disk space:")
    run_cmd(ssh, "df -h /", show_all=True)
    
    # Step 3: Clean up Docker
    print("\n" + "=" * 40)
    print("[3] DOCKER CLEANUP")
    print("=" * 40)
    run_cmd(ssh, f"echo '{VM_PASS}' | sudo -S docker system prune -af 2>&1 | tail -10", show_all=True)
    run_cmd(ssh, f"echo '{VM_PASS}' | sudo -S docker builder prune -af 2>&1 | tail -5", show_all=True)
    
    # Step 4: Pull latest code
    print("\n" + "=" * 40)
    print("[4] PULLING LATEST CODE")
    print("=" * 40)
    run_cmd(ssh, "cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main 2>&1", show_all=True)
    
    # Step 5: Build new Docker image
    print("\n" + "=" * 40)
    print("[5] BUILDING DOCKER IMAGE (5-10 min)")
    print("=" * 40)
    exit_code, out = run_cmd(ssh, 
        f"cd /opt/mycosoft/website && echo '{VM_PASS}' | sudo -S docker build -t website-website:latest --no-cache . 2>&1",
        timeout=900)
    
    if exit_code != 0:
        print("\n!!! BUILD FAILED !!!")
        ssh.close()
        return 1
    
    # Step 6: Restart containers
    print("\n" + "=" * 40)
    print("[6] RESTARTING CONTAINERS")
    print("=" * 40)
    run_cmd(ssh, f"echo '{VM_PASS}' | sudo -S docker stop mycosoft-website 2>/dev/null || true", show_all=True)
    run_cmd(ssh, f"echo '{VM_PASS}' | sudo -S docker rm mycosoft-website 2>/dev/null || true", show_all=True)
    run_cmd(ssh, f"cd /opt/mycosoft && echo '{VM_PASS}' | sudo -S docker compose -p mycosoft-production up -d mycosoft-website 2>&1", show_all=True)
    
    print("\nWaiting 30s for container startup...")
    time.sleep(30)
    
    # Step 7: Verify everything
    print("\n" + "=" * 40)
    print("[7] VERIFICATION")
    print("=" * 40)
    
    print("\nDocker containers:")
    run_cmd(ssh, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'", show_all=True)
    
    print("\nDisk space:")
    run_cmd(ssh, "df -h /", show_all=True)
    
    print("\nMemory:")
    run_cmd(ssh, "free -h", show_all=True)
    
    print("\nTesting localhost:3000...")
    exit_code, out = run_cmd(ssh, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000", show_all=True)
    
    print("\nTesting login page...")
    exit_code, out = run_cmd(ssh, "curl -s http://localhost:3000/login | head -c 500", show_all=True)
    
    # Step 8: Restart cloudflared
    print("\n" + "=" * 40)
    print("[8] RESTARTING CLOUDFLARED")
    print("=" * 40)
    run_cmd(ssh, f"echo '{VM_PASS}' | sudo -S systemctl restart cloudflared 2>&1", show_all=True)
    run_cmd(ssh, f"echo '{VM_PASS}' | sudo -S systemctl status cloudflared 2>&1 | head -10", show_all=True)
    
    ssh.close()
    
    print("\n" + "=" * 60)
    print("  ALL COMPLETE!")
    print("=" * 60)
    print("\nFinal steps:")
    print("1. Clear Cloudflare cache (PURGE EVERYTHING)")
    print("2. Test: https://sandbox.mycosoft.com")
    print("3. Test login: https://sandbox.mycosoft.com/login?redirectTo=%2Fdashboard%2Fcrep")
    print("4. Click Google/GitHub button and verify redirect")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
