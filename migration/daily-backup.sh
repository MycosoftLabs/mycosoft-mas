#!/bin/bash
# Daily VM Backup Script
# Run this on Proxmox server or via cron

set -e

VM_ID=100
VM_NAME="mycosoft-production"
BACKUP_STORAGE="local"
BACKUP_DIR="/mnt/mycosoft-nas/backups/vm-snapshots"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

echo "=========================================="
echo "Daily VM Backup: $VM_NAME"
echo "Date: $DATE"
echo "=========================================="

# Create backup directory
mkdir -p $BACKUP_DIR

# Check if running on Proxmox
if [ -f /etc/pve/.version ]; then
    # Running on Proxmox - use vzdump
    echo "Creating Proxmox backup..."
    vzdump $VM_ID \
        --storage $BACKUP_STORAGE \
        --compress gzip \
        --mode snapshot \
        --remove 0 \
        --dumpdir $BACKUP_DIR
    
    echo "Backup completed: $BACKUP_DIR/vzdump-qemu-$VM_ID-$DATE.vma.gz"
    
elif command -v ssh &> /dev/null; then
    # Running remotely - use SSH to Proxmox
    read -p "Enter Proxmox server IP: " PROXMOX_IP
    read -p "Enter Proxmox root user: " PROXMOX_USER
    
    echo "Creating backup via SSH..."
    ssh $PROXMOX_USER@$PROXMOX_IP "vzdump $VM_ID --storage $BACKUP_STORAGE --compress gzip --mode snapshot --remove 0"
    
    # Copy backup to NAS
    echo "Copying backup to NAS..."
    scp $PROXMOX_USER@$PROXMOX_IP:/var/lib/vz/dump/vzdump-qemu-$VM_ID-*.vma.gz $BACKUP_DIR/
    
else
    echo "ERROR: Cannot create backup. Must run on Proxmox or have SSH access."
    exit 1
fi

# Cleanup old backups
echo ""
echo "Cleaning up backups older than $RETENTION_DAYS days..."
find $BACKUP_DIR -name "*.vma.gz" -mtime +$RETENTION_DAYS -delete
echo "Cleanup completed"

# List current backups
echo ""
echo "Current backups:"
ls -lh $BACKUP_DIR/*.vma.gz 2>/dev/null | tail -5 || echo "No backups found"

echo ""
echo "=========================================="
echo "Backup completed successfully!"
echo "=========================================="
