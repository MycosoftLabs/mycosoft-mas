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

# Create cloud-init userdata to enable password SSH
print("\n=== Enabling password SSH via cloud-init ===")
cmd = """
# Stop VM first
qm stop 105 --timeout 30

# Create custom cloud-init snippet
mkdir -p /var/lib/vz/snippets

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
  - echo "SSH password auth enabled"
package_update: true
packages:
  - docker.io
  - docker-compose
  - curl
  - wget
  - git
  - htop
  - net-tools
CLOUDINIT

# Set snippet
qm set 105 --cicustom "user=local:snippets/mindex-user.yml"

# Regenerate cloud-init
qm cloudinit dump 105 user

# Start VM
qm start 105

echo "VM reconfigured and starting..."
"""

stdin, stdout, stderr = ssh.exec_command(cmd)
time.sleep(45)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print(f"Errors: {err}")

# Check status
print("\n=== VM Status ===")
stdin, stdout, stderr = ssh.exec_command("qm status 105")
time.sleep(2)
print(stdout.read().decode())

ssh.close()
