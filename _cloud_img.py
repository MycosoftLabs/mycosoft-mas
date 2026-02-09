import paramiko
import time

proxmox_host = "192.168.0.90"
proxmox_user = "root"
proxmox_pass = "20202020"

print("Connecting to Proxmox...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(proxmox_host, username=proxmox_user, password=proxmox_pass, timeout=15)
print("Connected!")

# Check download progress and use cloud image if needed
print("\n=== Checking ISO download and using cloud image ===")
cmd = """
# Check if regular ISO download is happening
ps aux | grep wget | grep -v grep

# Download Ubuntu cloud image instead (faster, ~700MB)
cd /var/lib/vz/template/iso/
if [ ! -f ubuntu-22.04-server-cloudimg-amd64.img ]; then
    echo "Downloading Ubuntu 22.04 cloud image (~700MB)..."
    wget -q https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img -O ubuntu-22.04-server-cloudimg-amd64.img
    echo "Cloud image downloaded!"
fi

# List what we have
ls -la /var/lib/vz/template/iso/
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(60)  # Wait for download
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print(f"Errors: {err}")

ssh.close()
