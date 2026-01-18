#!/bin/bash
# Proxmox VM Creation Script
# Run this on Proxmox server to create VMs

set -e

VM1_ID=100
VM2_ID=101
VM1_NAME="mycosoft-production"
VM2_NAME="mycosoft-operator"

echo "=========================================="
echo "Creating Mycosoft Production VMs"
echo "=========================================="

# Check if running on Proxmox
if [ ! -f /etc/pve/.version ]; then
    echo "ERROR: This script must be run on a Proxmox server"
    exit 1
fi

# Create VM1 (Production)
echo "Creating VM1: $VM1_NAME (ID: $VM1_ID)"
qm create $VM1_ID \
    --name $VM1_NAME \
    --memory 262144 \
    --cores 16 \
    --sockets 2 \
    --cpu host \
    --net0 virtio,bridge=vmbr0,firewall=1 \
    --scsi0 local-lvm:0,discard=on,cache=writeback,size=2000G \
    --boot order=scsi0 \
    --agent enabled=1 \
    --ostype l26 \
    --machine q35 \
    --bios ovmf

# Create VM2 (Code Operator)
echo "Creating VM2: $VM2_NAME (ID: $VM2_ID)"
qm create $VM2_ID \
    --name $VM2_NAME \
    --memory 65536 \
    --cores 8 \
    --sockets 1 \
    --cpu host \
    --net0 virtio,bridge=vmbr0,firewall=1 \
    --scsi0 local-lvm:0,discard=on,cache=writeback,size=500G \
    --boot order=scsi0 \
    --agent enabled=1 \
    --ostype l26 \
    --machine q35 \
    --bios ovmf

echo ""
echo "=========================================="
echo "VMs created successfully!"
echo "=========================================="
echo "VM1: $VM1_NAME (ID: $VM1_ID) - 256GB RAM, 16 cores, 2TB disk"
echo "VM2: $VM2_NAME (ID: $VM2_ID) - 64GB RAM, 8 cores, 500GB disk"
echo ""
echo "Next steps:"
echo "1. Download Ubuntu 22.04 LTS ISO if not already present"
echo "2. Attach ISO to VM1 and VM2"
echo "3. Start VMs and install Ubuntu"
echo "4. Run os-setup.sh on each VM after installation"
