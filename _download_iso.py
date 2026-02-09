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

# Download Ubuntu 22.04 Server ISO
print("\n=== Downloading Ubuntu 22.04 Server ISO ===")
download_cmd = """
cd /var/lib/vz/template/iso/
if [ ! -f ubuntu-22.04.4-live-server-amd64.iso ]; then
    echo "Downloading Ubuntu 22.04.4 LTS Server..."
    wget -q --show-progress https://releases.ubuntu.com/22.04.4/ubuntu-22.04.4-live-server-amd64.iso
    echo "Download complete!"
else
    echo "ISO already exists"
fi
ls -la /var/lib/vz/template/iso/
"""
stdin, stdout, stderr = ssh.exec_command(download_cmd)
# This will take a while for download
print("Starting ISO download (this may take several minutes)...")
print("Checking if ISO exists or needs download...")

# Wait and get output
time.sleep(5)
output = stdout.read().decode()
errors = stderr.read().decode()
print(output)
if errors:
    print(f"Errors: {errors}")

ssh.close()
