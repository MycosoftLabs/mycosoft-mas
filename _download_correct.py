import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

proxmox_host = "192.168.0.202"
proxmox_user = "root"
proxmox_pass = "20202020"

print(f"Connecting to correct Proxmox at {proxmox_host}...")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(proxmox_host, username=proxmox_user, password=proxmox_pass, timeout=15)
print("Connected!")

# First check for Ubuntu cloud image
print("\n=== Checking for cloud image ===")
stdin, stdout, stderr = ssh.exec_command("ls -la /var/lib/vz/template/iso/ 2>/dev/null")
time.sleep(2)
print(stdout.read().decode('utf-8', errors='replace'))

# Download cloud image if needed
print("\n=== Downloading Ubuntu cloud image ===")
cmd = '''
cd /var/lib/vz/template/iso/
if [ ! -f ubuntu-22.04-server-cloudimg-amd64.img ]; then
    echo "Downloading Ubuntu 22.04 cloud image..."
    wget -q https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img -O ubuntu-22.04-server-cloudimg-amd64.img
    echo "Download complete!"
else
    echo "Cloud image already exists"
fi
ls -la ubuntu-22.04-server-cloudimg-amd64.img
'''
stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(60)  # Wait for download
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
print("Image ready!")
