#!/bin/bash
# Script to expand LVM after Proxmox disk expansion
# Run this AFTER expanding the virtual disk in Proxmox

set -e

echo "=========================================="
echo "LVM EXPANSION SCRIPT"
echo "=========================================="
echo ""
echo "WARNING: This script will expand the LVM partition."
echo "Make sure you have expanded the virtual disk in Proxmox first!"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Check current disk usage
echo ""
echo "[1] Current disk usage:"
df -h /

# Detect disk device (usually sda for first disk)
DISK_DEVICE=$(lsblk -dn -o NAME,TYPE | grep disk | head -1 | awk '{print $1}')
DISK_PATH="/dev/${DISK_DEVICE}"
PARTITION_PATH="${DISK_PATH}3"  # Usually partition 3 for LVM

echo ""
echo "[2] Detected disk: ${DISK_PATH}"
echo "    Partition: ${PARTITION_PATH}"

# Resize physical volume
echo ""
echo "[3] Resizing physical volume..."
sudo pvresize ${PARTITION_PATH}

# Extend logical volume to use all free space
echo ""
echo "[4] Extending logical volume..."
sudo lvextend -l +100%FREE /dev/ubuntu-vg/ubuntu-lv

# Resize filesystem
echo ""
echo "[5] Resizing filesystem..."
sudo resize2fs /dev/mapper/ubuntu--vg-ubuntu--lv

# Final disk usage
echo ""
echo "[6] Final disk usage:"
df -h /

echo ""
echo "=========================================="
echo "LVM EXPANSION COMPLETE!"
echo "=========================================="
