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

# Create MINDEX VM (ID 189)
print("\n=== Creating MINDEX VM (ID 189) ===")
vm_create_cmd = '''
# VM Configuration
VM_ID=189
VM_NAME="MINDEX-VM"
MEMORY=8192
CORES=4
DISK_SIZE=100G
CLOUD_IMG="/var/lib/vz/template/iso/ubuntu-22.04-server-cloudimg-amd64.img"

# Check if VM exists
if qm status $VM_ID 2>/dev/null; then
    echo "VM $VM_ID already exists!"
    qm status $VM_ID
    exit 0
fi

echo "Creating VM $VM_ID ($VM_NAME)..."

# Create the VM
qm create $VM_ID --name $VM_NAME --memory $MEMORY --cores $CORES --net0 virtio,bridge=vmbr0 --ostype l26

# Import the cloud image to local-lvm storage
echo "Importing cloud image..."
qm importdisk $VM_ID $CLOUD_IMG local-lvm

# Attach the disk
echo "Attaching disk..."
qm set $VM_ID --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-$VM_ID-disk-0

# Add cloud-init drive
echo "Adding cloud-init drive..."
qm set $VM_ID --ide2 local-lvm:cloudinit

# Set boot order
qm set $VM_ID --boot c --bootdisk scsi0

# Resize disk to 100GB
echo "Resizing disk to $DISK_SIZE..."
qm resize $VM_ID scsi0 $DISK_SIZE

# Configure cloud-init
echo "Configuring cloud-init..."
qm set $VM_ID --ciuser mycosoft
qm set $VM_ID --cipassword 'REDACTED_VM_SSH_PASSWORD'
qm set $VM_ID --ipconfig0 ip=192.168.0.189/24,gw=192.168.0.1
qm set $VM_ID --nameserver 8.8.8.8
qm set $VM_ID --searchdomain local
qm set $VM_ID --serial0 socket --vga serial0

# Enable agent
qm set $VM_ID --agent enabled=1

# Add description
qm set $VM_ID --description "MINDEX VM - Memory Index & Knowledge Graph Server. Created 2026-02-04."

echo "VM $VM_ID created successfully!"
qm config $VM_ID
'''

channel = ssh.get_transport().open_session()
channel.exec_command(vm_create_cmd)
time.sleep(45)

output = channel.recv(65535).decode('utf-8', errors='replace')
print(output)

ssh.close()
print("VM creation complete!")
