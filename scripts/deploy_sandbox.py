#!/usr/bin/env python3
"""
Deploy Sandbox - Full deployment to sandbox.mycosoft.com
Uses correct paths at /opt/mycosoft/
"""

import paramiko
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# VM Configuration
VM_HOST = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "REDACTED_VM_SSH_PASSWORD"

# Correct paths on VM
WEBSITE_PATH = "/opt/mycosoft/website"
ASSETS_PATH = f"{WEBSITE_PATH}/public/assets/mushroom1"

# Local paths
LOCAL_WEBSITE = Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website")
LOCAL_MUSHROOM1 = LOCAL_WEBSITE / "public" / "assets" / "mushroom1"

def run(client, cmd, show=True):
    """Run SSH command"""
    print(f"[CMD] {cmd[:100]}...")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=600)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    exit_code = stdout.channel.recv_exit_status()
    if show and out:
        for line in out.split('\n')[-20:]:
            print(f"      {line}")
    if err and exit_code != 0:
        print(f"[ERR] {err[:300]}")
    return exit_code == 0, out

def upload_folder(sftp, local_dir, remote_dir, extensions):
    """Upload files matching extensions"""
    count = 0
    total_mb = 0
    for f in Path(local_dir).iterdir():
        if f.is_file() and f.suffix.lower() in extensions:
            remote_file = f"{remote_dir}/{f.name}"
            size_mb = f.stat().st_size / (1024*1024)
            print(f"      Uploading {f.name} ({size_mb:.1f}MB)")
            sftp.put(str(f), remote_file)
            count += 1
            total_mb += size_mb
    return count, total_mb

def main():
    start = time.time()
    print("=" * 60)
    print("MYCOSOFT SANDBOX DEPLOYMENT")
    print("=" * 60)
    
    # Connect
    print("\n[1/6] Connecting to VM...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
    print("      Connected to 192.168.0.187")
    
    # Check if website directory exists, clone if not
    print("\n[2/6] Checking website repository...")
    success, out = run(client, f"test -d {WEBSITE_PATH}/.git && echo EXISTS || echo MISSING", show=False)
    
    if "MISSING" in out:
        print("      Cloning website repository...")
        run(client, f"sudo mkdir -p {WEBSITE_PATH} && sudo chown mycosoft:mycosoft {WEBSITE_PATH}")
        run(client, f"git clone https://github.com/MycosoftLabs/website.git {WEBSITE_PATH}")
    else:
        print("      Pulling latest changes...")
        run(client, f"cd {WEBSITE_PATH} && git fetch origin && git reset --hard origin/main")
    
    # Upload video files
    print("\n[3/6] Uploading video files (bypassing GitHub 100MB limit)...")
    run(client, f"mkdir -p {ASSETS_PATH}")
    
    sftp = client.open_sftp()
    vcount, vsize = upload_folder(sftp, LOCAL_MUSHROOM1, ASSETS_PATH, ['.mp4'])
    print(f"      Uploaded {vcount} videos ({vsize:.0f}MB)")
    
    # Upload images
    print("\n[4/6] Syncing image assets...")
    icount, isize = upload_folder(sftp, LOCAL_MUSHROOM1, ASSETS_PATH, ['.jpg', '.jpeg', '.png', '.gif', '.webp'])
    print(f"      Synced {icount} images ({isize:.0f}MB)")
    sftp.close()
    
    # Rebuild Docker
    print("\n[5/6] Rebuilding website Docker image...")
    run(client, f"cd {WEBSITE_PATH} && docker build -t website-website:latest . 2>&1 | tail -30")
    
    # Restart container
    print("\n[6/6] Restarting website container...")
    run(client, "docker stop mycosoft-website 2>/dev/null; docker rm mycosoft-website 2>/dev/null; true")
    run(client, f"cd /opt/mycosoft && docker compose up -d mycosoft-website")
    
    # Wait and verify
    print("\n[VERIFY] Checking deployment status...")
    time.sleep(8)
    run(client, "docker ps --filter name=website --format 'table {{.Names}}\t{{.Status}}'")
    run(client, "curl -s -o /dev/null -w 'HTTP %{http_code}' http://localhost:3000")
    
    client.close()
    
    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"DEPLOYMENT COMPLETE ({elapsed:.0f}s)")
    print(f"{'='*60}")
    print(f"Local:  http://192.168.0.187:3000")
    print(f"Public: https://sandbox.mycosoft.com")

if __name__ == "__main__":
    main()
