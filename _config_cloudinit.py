import paramiko
import time
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

proxmox_host = "192.168.0.202"
proxmox_user = "root"
proxmox_pass = "20202020"

print(f"Connecting to Proxmox at {proxmox_host}...")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(proxmox_host, username=proxmox_user, password=proxmox_pass, timeout=15)
print("Connected!")

# Create cloud-init snippet with password auth enabled
print("\n=== Creating cloud-init snippet ===")
cmd = '''
# Stop VM
qm stop 189 --timeout 30

# Create snippets directory
mkdir -p /var/lib/vz/snippets

# Create cloud-init user config
cat > /var/lib/vz/snippets/mindex-user.yml << 'CLOUDINIT'
#cloud-config
users:
  - name: mycosoft
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    lock_passwd: false
    plain_text_passwd: 'Mushroom1!Mushroom1!'
ssh_pwauth: true
disable_root: false
chpasswd:
  list: |
    root:Mushroom1!Mushroom1!
    mycosoft:Mushroom1!Mushroom1!
  expire: false
runcmd:
  - sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
  - sed -i 's/^#*PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
  - systemctl restart sshd
  - apt-get update -qq
  - apt-get install -y docker.io docker-compose curl wget git htop
  - systemctl enable docker
  - systemctl start docker
  - usermod -aG docker mycosoft
  - mkdir -p /opt/mycosoft/ledger /opt/mycosoft/mindex /data/postgres /data/redis /data/qdrant
  - chown -R mycosoft:mycosoft /opt/mycosoft
  - chown -R 999:999 /data/postgres
CLOUDINIT

# Set snippet on VM
qm set 189 --cicustom "user=local:snippets/mindex-user.yml"

# Start VM
qm start 189

echo "VM reconfigured and started"
qm status 189
'''

stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(45)
print(stdout.read().decode('utf-8', errors='replace'))
err = stderr.read().decode('utf-8', errors='replace')
if err:
    print(err)

ssh.close()
print("Done!")
