#!/bin/bash
# NAS Mount Configuration for MINDEX VM
# Created: February 4, 2026

# This script configures the NAS mount for ledger file backup

set -e

echo "=== MINDEX VM NAS Mount Configuration ==="

# Configuration
NAS_IP="192.168.0.105"
NAS_SHARE="mycosoft/ledger"
MOUNT_POINT="/opt/mycosoft/ledger"
CREDENTIALS_FILE="/etc/samba/credentials"

# Create mount point
echo "Creating mount point..."
sudo mkdir -p $MOUNT_POINT
sudo mkdir -p /etc/samba

# Create credentials file (will be prompted for password)
echo "Creating credentials file..."
cat << EOF | sudo tee $CREDENTIALS_FILE > /dev/null
username=mycosoft
password=REPLACE_WITH_ACTUAL_PASSWORD
domain=WORKGROUP
EOF
sudo chmod 600 $CREDENTIALS_FILE

# Install CIFS utils if not present
echo "Installing CIFS utilities..."
sudo apt-get update
sudo apt-get install -y cifs-utils

# Add to fstab for persistent mount
echo "Adding to fstab..."
FSTAB_ENTRY="//${NAS_IP}/${NAS_SHARE} ${MOUNT_POINT} cifs credentials=${CREDENTIALS_FILE},uid=1000,gid=1000,iocharset=utf8,file_mode=0664,dir_mode=0775 0 0"

if ! grep -q "${NAS_SHARE}" /etc/fstab; then
    echo "$FSTAB_ENTRY" | sudo tee -a /etc/fstab
    echo "Added fstab entry"
else
    echo "Fstab entry already exists"
fi

# Mount the share
echo "Mounting NAS share..."
sudo mount -a

# Verify mount
if mountpoint -q $MOUNT_POINT; then
    echo "SUCCESS: NAS share mounted at $MOUNT_POINT"
    ls -la $MOUNT_POINT
else
    echo "WARNING: Mount failed. Please check credentials and network."
fi

# Create subdirectories for ledger data
echo "Creating ledger directories..."
sudo mkdir -p $MOUNT_POINT/chain
sudo mkdir -p $MOUNT_POINT/backups
sudo mkdir -p $MOUNT_POINT/snapshots

# Set permissions
sudo chown -R mycosoft:mycosoft $MOUNT_POINT
sudo chmod -R 775 $MOUNT_POINT

echo "=== NAS Mount Configuration Complete ==="
echo ""
echo "Next steps:"
echo "1. Edit $CREDENTIALS_FILE and replace REPLACE_WITH_ACTUAL_PASSWORD"
echo "2. Run: sudo mount -a"
echo "3. Verify: mountpoint $MOUNT_POINT"