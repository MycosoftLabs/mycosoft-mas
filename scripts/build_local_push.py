#!/usr/bin/env python3
"""Build Docker image locally and push to VM via docker save/load."""
import subprocess
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

WEBSITE_DIR = r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website"
IMAGE_NAME = "website-website:latest"
TEMP_TAR = r"C:\Users\admin2\Desktop\website-image.tar"

def run(cmd, cwd=None):
    print(f"\n>>> {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=False)
    return result.returncode

def main():
    print("=" * 60)
    print("  LOCAL BUILD & PUSH TO VM")
    print("=" * 60)
    
    # Step 1: Build Docker image locally
    print("\n[1/5] Building Docker image locally...")
    print("This will build using your Windows Docker Desktop")
    
    # Check if Docker is running
    if run("docker version") != 0:
        print("ERROR: Docker is not running! Please start Docker Desktop.")
        return
    
    # Build the image
    ret = run(f"docker build -t {IMAGE_NAME} -f Dockerfile.production .", cwd=WEBSITE_DIR)
    if ret != 0:
        print("ERROR: Docker build failed!")
        return
    
    print("\n[2/5] Image built successfully!")
    
    # Step 2: Save image to tar file
    print("\n[3/5] Saving image to tar file...")
    ret = run(f"docker save {IMAGE_NAME} -o {TEMP_TAR}")
    if ret != 0:
        print("ERROR: Failed to save image!")
        return
    
    file_size = os.path.getsize(TEMP_TAR) / (1024 * 1024 * 1024)
    print(f"Image saved: {file_size:.2f} GB")
    
    # Step 3: Transfer to VM via SCP
    print("\n[4/5] Transferring image to VM (this may take a while)...")
    ret = run(f'scp {TEMP_TAR} mycosoft@192.168.0.187:/home/mycosoft/website-image.tar')
    if ret != 0:
        print("ERROR: Failed to transfer image! Trying with PowerShell...")
        # Try with paramiko
        import paramiko
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect('192.168.0.187', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=30)
        
        sftp = client.open_sftp()
        print(f"Uploading {file_size:.2f} GB - please wait...")
        sftp.put(TEMP_TAR, '/home/mycosoft/website-image.tar')
        sftp.close()
        client.close()
    
    # Step 4: Load image on VM and restart container
    print("\n[5/5] Loading image on VM and restarting container...")
    import paramiko
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('192.168.0.187', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=30)
    
    commands = [
        'docker load -i /home/mycosoft/website-image.tar',
        'docker stop mycosoft-website 2>/dev/null || true',
        'docker rm mycosoft-website 2>/dev/null || true',
        'docker run -d --name mycosoft-website -p 3000:3000 --restart unless-stopped website-website:latest',
        'docker ps | grep website',
    ]
    
    for cmd in commands:
        print(f"\n>>> {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
        print(stdout.read().decode('utf-8', errors='replace'))
        err = stderr.read().decode('utf-8', errors='replace')
        if err:
            print(f"[STDERR] {err}")
    
    client.close()
    
    # Cleanup local tar file
    print("\nCleaning up local tar file...")
    os.remove(TEMP_TAR)
    
    print("\n" + "=" * 60)
    print("  DONE! Website should now be running with new code.")
    print("=" * 60)
    print("\nTest at: https://sandbox.mycosoft.com/devices/mushroom-1")

if __name__ == "__main__":
    main()
