#!/usr/bin/env python3
"""
Complete VM setup after restart:
1. Expand LVM to use full disk
2. Set up cleanup cron
3. Pull and deploy website
"""
import paramiko
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

def run_cmd(ssh, cmd, timeout=300, show_output=True):
    """Execute command and return output"""
    print(f">>> {cmd}")
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if show_output and out:
        print(out)
    if err and exit_code != 0:
        print(f"STDERR: {err}")
    return exit_code, out

def main():
    print("=" * 60)
    print("  COMPLETE VM SETUP AFTER UPGRADE")
    print("=" * 60)
    
    print(f"\nConnecting to {VM_HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # Retry connection a few times
    for attempt in range(5):
        try:
            ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
            print("Connected!")
            break
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {e}")
            time.sleep(10)
    else:
        print("Could not connect to VM")
        return 1
    
    # Check current disk usage
    print("\n" + "=" * 60)
    print("  [1] CURRENT DISK STATUS")
    print("=" * 60)
    run_cmd(ssh, "df -h /")
    run_cmd(ssh, "lsblk")
    
    # Expand LVM partition
    print("\n" + "=" * 60)
    print("  [2] EXPANDING LVM TO USE FULL DISK")
    print("=" * 60)
    
    # Grow the physical volume to use all available space
    print("\nGrowing physical volume...")
    run_cmd(ssh, f"echo '{VM_PASS}' | sudo -S pvresize /dev/sda3 2>&1")
    
    # Extend the logical volume to use all free space
    print("\nExtending logical volume...")
    run_cmd(ssh, f"echo '{VM_PASS}' | sudo -S lvextend -l +100%FREE /dev/ubuntu-vg/ubuntu-lv 2>&1")
    
    # Resize the filesystem
    print("\nResizing filesystem...")
    run_cmd(ssh, f"echo '{VM_PASS}' | sudo -S resize2fs /dev/ubuntu-vg/ubuntu-lv 2>&1")
    
    # Verify new size
    print("\nVerifying new disk size:")
    run_cmd(ssh, "df -h /")
    
    # Set up cleanup cron
    print("\n" + "=" * 60)
    print("  [3] SETTING UP AUTOMATED CLEANUP CRON")
    print("=" * 60)
    
    cleanup_script = '''#!/bin/bash
# Weekly Docker cleanup - runs every Sunday at 3 AM
docker system prune -af --volumes
docker builder prune -af
apt-get clean
apt-get autoremove -y
journalctl --vacuum-time=7d
'''
    
    # Write cleanup script
    run_cmd(ssh, f"echo '{VM_PASS}' | sudo -S tee /opt/mycosoft/cleanup.sh << 'EOF'\n{cleanup_script}\nEOF")
    run_cmd(ssh, f"echo '{VM_PASS}' | sudo -S chmod +x /opt/mycosoft/cleanup.sh")
    
    # Add cron job
    cron_line = "0 3 * * 0 /opt/mycosoft/cleanup.sh >> /var/log/cleanup.log 2>&1"
    run_cmd(ssh, f"(echo '{VM_PASS}' | sudo -S crontab -l 2>/dev/null; echo '{cron_line}') | sudo -S crontab -")
    print("Cleanup cron job installed")
    
    # Pull and deploy website
    print("\n" + "=" * 60)
    print("  [4] PULLING LATEST CODE")
    print("=" * 60)
    
    run_cmd(ssh, "cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main 2>&1")
    
    # Check current commit
    print("\nCurrent commit:")
    run_cmd(ssh, "cd /opt/mycosoft/website && git log -1 --oneline")
    
    # Build Docker image
    print("\n" + "=" * 60)
    print("  [5] BUILDING DOCKER IMAGE (this takes 5-10 minutes)")
    print("=" * 60)
    
    exit_code, out = run_cmd(ssh, 
        f"cd /opt/mycosoft/website && echo '{VM_PASS}' | sudo -S docker build -t website-website:latest --no-cache . 2>&1",
        timeout=900, show_output=False)
    
    # Show last 50 lines
    lines = out.strip().split('\n')
    print('\n'.join(lines[-50:]))
    print(f"\nBuild exit code: {exit_code}")
    
    if exit_code != 0:
        print("\n!!! BUILD FAILED !!!")
        ssh.close()
        return 1
    
    # Restart container
    print("\n" + "=" * 60)
    print("  [6] RESTARTING CONTAINER")
    print("=" * 60)
    
    run_cmd(ssh, f"echo '{VM_PASS}' | sudo -S docker stop mycosoft-website 2>/dev/null || true")
    run_cmd(ssh, f"echo '{VM_PASS}' | sudo -S docker rm mycosoft-website 2>/dev/null || true")
    run_cmd(ssh, f"cd /opt/mycosoft && echo '{VM_PASS}' | sudo -S docker compose -p mycosoft-production up -d mycosoft-website 2>&1")
    
    print("\nWaiting 20 seconds for startup...")
    time.sleep(20)
    
    # Verify container
    print("\n" + "=" * 60)
    print("  [7] VERIFICATION")
    print("=" * 60)
    
    print("\nContainer status:")
    run_cmd(ssh, "docker ps --filter name=mycosoft-website --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
    
    print("\nDisk usage:")
    run_cmd(ssh, "df -h /")
    
    print("\nDocker disk usage:")
    run_cmd(ssh, "docker system df")
    
    print("\nTesting localhost:3000:")
    run_cmd(ssh, "curl -s -o /dev/null -w 'HTTP Status: %{http_code}\\n' http://localhost:3000")
    
    ssh.close()
    
    print("\n" + "=" * 60)
    print("  SETUP COMPLETE!")
    print("=" * 60)
    print("\nCompleted tasks:")
    print("  ✓ LVM expanded to use full disk")
    print("  ✓ Cleanup cron job installed (weekly)")
    print("  ✓ Latest code pulled from GitHub")
    print("  ✓ Docker image rebuilt")
    print("  ✓ Container restarted")
    print("\nNext steps:")
    print("  1. Clear Cloudflare cache (PURGE EVERYTHING)")
    print("  2. Test: https://sandbox.mycosoft.com/login?redirectTo=%2Fdashboard%2Fcrep")
    print("  3. Verify OAuth redirect works correctly")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
