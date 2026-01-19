#!/usr/bin/env python3
"""
Fast Deploy Script - Deploys website with all assets to sandbox
Uses Paramiko for SSH/SFTP with password auth
"""

import paramiko
import os
import sys
from pathlib import Path
import time

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# VM Configuration
VM_HOST = "192.168.0.187"
VM_USER = "mycosoft"
VM_PASS = "Mushroom1!Mushroom1!"
REMOTE_PATH = "/home/mycosoft/website"

# Local paths
LOCAL_WEBSITE = Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website")
LOCAL_MUSHROOM1 = LOCAL_WEBSITE / "public" / "assets" / "mushroom1"

def create_ssh_client():
    """Create SSH client with password auth"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"🔌 Connecting to {VM_HOST}...")
    client.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
    print("✅ Connected!")
    return client

def run_command(client, cmd, show_output=True):
    """Run command on remote server"""
    print(f"📌 Running: {cmd[:80]}...")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=300)
    exit_code = stdout.channel.recv_exit_status()
    
    if show_output:
        output = stdout.read().decode('utf-8').strip()
        errors = stderr.read().decode('utf-8').strip()
        if output:
            print(f"   {output[:500]}")
        if errors and exit_code != 0:
            print(f"   ⚠️ {errors[:500]}")
    
    return exit_code == 0

def upload_files(client, local_dir, remote_dir, extensions=None):
    """Upload files via SFTP"""
    sftp = client.open_sftp()
    
    # Ensure remote directory exists
    try:
        sftp.stat(remote_dir)
    except:
        run_command(client, f"mkdir -p {remote_dir}")
    
    local_path = Path(local_dir)
    files_uploaded = 0
    total_size = 0
    
    for file in local_path.iterdir():
        if file.is_file():
            if extensions and file.suffix.lower() not in extensions:
                continue
            
            remote_file = f"{remote_dir}/{file.name}"
            file_size = file.stat().st_size / (1024 * 1024)  # MB
            
            print(f"   📤 {file.name} ({file_size:.1f} MB)...")
            sftp.put(str(file), remote_file)
            files_uploaded += 1
            total_size += file_size
    
    sftp.close()
    return files_uploaded, total_size

def main():
    start_time = time.time()
    print("=" * 60)
    print("🚀 MYCOSOFT FAST DEPLOY - Sandbox Deployment")
    print("=" * 60)
    
    try:
        client = create_ssh_client()
        
        # Step 1: Pull latest code from GitHub
        print("\n📦 Step 1: Pulling latest code from GitHub...")
        run_command(client, f"cd {REMOTE_PATH} && git fetch origin && git reset --hard origin/main")
        
        # Step 2: Upload video files that aren't in Git
        print("\n📹 Step 2: Uploading video files (too large for GitHub)...")
        remote_mushroom1 = f"{REMOTE_PATH}/public/assets/mushroom1"
        run_command(client, f"mkdir -p {remote_mushroom1}")
        
        files, size = upload_files(client, LOCAL_MUSHROOM1, remote_mushroom1, extensions=['.mp4'])
        print(f"   ✅ Uploaded {files} video files ({size:.1f} MB total)")
        
        # Step 3: Also upload any images that might be missing
        print("\n🖼️ Step 3: Syncing image files...")
        files2, size2 = upload_files(client, LOCAL_MUSHROOM1, remote_mushroom1, extensions=['.jpg', '.jpeg', '.png', '.gif', '.webp'])
        print(f"   ✅ Synced {files2} image files ({size2:.1f} MB)")
        
        # Step 4: Rebuild Docker image
        print("\n🐳 Step 4: Rebuilding Docker image (this may take a few minutes)...")
        run_command(client, f"cd {REMOTE_PATH} && docker build -t mycosoft-website:latest --no-cache . 2>&1 | tail -20")
        
        # Step 5: Restart container
        print("\n🔄 Step 5: Restarting container...")
        run_command(client, f"cd {REMOTE_PATH} && docker compose down mycosoft-website 2>/dev/null || true")
        run_command(client, f"cd {REMOTE_PATH} && docker compose up -d mycosoft-website")
        
        # Step 6: Verify deployment
        print("\n✅ Step 6: Verifying deployment...")
        time.sleep(5)
        run_command(client, "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'website|NAME'")
        run_command(client, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000 && echo ' - Website responding'")
        
        client.close()
        
        elapsed = time.time() - start_time
        print("\n" + "=" * 60)
        print(f"🎉 DEPLOYMENT COMPLETE in {elapsed:.1f} seconds!")
        print("=" * 60)
        print(f"\n🌐 Live at: https://sandbox.mycosoft.com")
        print(f"📁 Local:   http://192.168.0.187:3000")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
