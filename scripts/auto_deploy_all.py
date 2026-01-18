import paramiko
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

def run(ssh, cmd, timeout=300):
    print(f'\n> {cmd[:80]}...' if len(cmd) > 80 else f'\n> {cmd}')
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    exit_code = out.channel.recv_exit_status()
    output = out.read().decode('utf-8', errors='replace')
    if output.strip():
        print(output.strip()[:2000])
    return output, exit_code

print("=" * 70)
print("AUTOMATED DEPLOYMENT - ALL STEPS")
print("=" * 70)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

# Step 1: Pull latest code
print("\n[1] Pulling latest code from GitHub...")
run(ssh, "cd ~/mycosoft-mas && git fetch origin")
run(ssh, "cd ~/mycosoft-mas && git reset --hard origin/main")

# Get latest commit
output, _ = run(ssh, "cd ~/mycosoft-mas && git log -1 --oneline")
print(f"Latest commit: {output.strip()}")

# Step 2: Upload and set up cleanup cron script
print("\n[2] Setting up automated cleanup cron...")
cleanup_cron_script = """#!/bin/bash
# Weekly Docker cleanup script
# Removes unused images, containers, volumes older than 7 days

LOG_FILE="/var/log/docker-cleanup.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[${DATE}] Starting Docker cleanup..." >> ${LOG_FILE}

# Get disk usage before
BEFORE=$(df -h / | awk 'NR==2 {print $5}')

# Clean up resources older than 7 days (168 hours)
docker system prune -af --filter "until=168h" >> ${LOG_FILE} 2>&1
docker builder prune -af --keep-storage=2GB >> ${LOG_FILE} 2>&1
docker volume prune -f >> ${LOG_FILE} 2>&1

# Get disk usage after
AFTER=$(df -h / | awk 'NR==2 {print $5}')

echo "[${DATE}] Cleanup complete. Disk usage: ${BEFORE} -> ${AFTER}" >> ${LOG_FILE}
"""

# Create cleanup script
sftp = ssh.open_sftp()
with sftp.file('/tmp/docker-cleanup.sh', 'w') as f:
    f.write(cleanup_cron_script)
sftp.chmod('/tmp/docker-cleanup.sh', 0o755)
sftp.close()

# Move to final location
run(ssh, f'echo "{VM_PASS}" | sudo -S mv /tmp/docker-cleanup.sh /usr/local/bin/docker-cleanup.sh')
run(ssh, f'echo "{VM_PASS}" | sudo -S chmod +x /usr/local/bin/docker-cleanup.sh')

# Add to crontab
cron_job = "0 3 * * 0 /usr/local/bin/docker-cleanup.sh"
run(ssh, f'echo "{VM_PASS}" | sudo -S crontab -l 2>/dev/null | grep -v "docker-cleanup.sh" | sudo crontab - || true')
run(ssh, f'echo "{VM_PASS}" | sudo -S bash -c "(crontab -l 2>/dev/null; echo \"{cron_job}\") | crontab -"')

print("\n[3] Cleanup cron scheduled: Every Sunday at 3 AM")

# Step 3: Pull website code and rebuild
print("\n[4] Pulling website code and rebuilding...")
run(ssh, "cd ~/mycosoft-mas && git submodule update --init --recursive || true")

# Rebuild website Docker image
print("\n[5] Rebuilding Docker image (this may take 5-10 minutes)...")
run(ssh, "cd ~/mycosoft-mas && echo '{VM_PASS}' | sudo -S docker-compose -f docker-compose.always-on.yml build mycosoft-website --no-cache", timeout=900)

# Step 4: Restart container
print("\n[6] Restarting website container...")
run(ssh, f"cd ~/mycosoft-mas && echo '{VM_PASS}' | sudo -S docker-compose -f docker-compose.always-on.yml up -d mycosoft-website")

time.sleep(5)

# Step 5: Verify services
print("\n[7] Verifying services...")
run(ssh, "docker ps | grep mycosoft-website")
run(ssh, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000")
run(ssh, f'echo "{VM_PASS}" | sudo -S systemctl status cloudflared --no-pager | head -10')

# Step 6: Check container logs
print("\n[8] Recent container logs:")
run(ssh, "docker logs mycosoft-website --tail 20")

print("\n" + "=" * 70)
print("DEPLOYMENT COMPLETE!")
print("=" * 70)
print("\nNext steps:")
print("1. Test login at https://sandbox.mycosoft.com/login")
print("2. Navigate between pages to verify session persistence")
print("3. Check cron job: sudo crontab -l")
print("4. Monitor cleanup logs: tail -f /var/log/docker-cleanup.log")

ssh.close()
