#!/bin/bash
# NAS Mount Setup Script
# Run this on VM1 to setup NAS mounting

set -e

echo "=========================================="
echo "NAS Mount Setup"
echo "=========================================="

MOUNT_POINT="/mnt/mycosoft-nas"

# Prompt for NAS configuration
echo "Select NAS protocol:"
echo "1) NFS"
echo "2) SMB/CIFS"
read -p "Enter choice (1 or 2): " PROTOCOL

read -p "Enter NAS IP address: " NAS_IP
read -p "Enter NAS share path (e.g., /mycosoft-data or mycosoft-data): " SHARE_PATH

# Create mount point
sudo mkdir -p $MOUNT_POINT

if [ "$PROTOCOL" = "1" ]; then
    # NFS Setup
    echo "Setting up NFS mount..."
    sudo apt install -y nfs-common
    
    read -p "Enter NFS options (default: defaults,_netdev): " NFS_OPTS
    NFS_OPTS=${NFS_OPTS:-defaults,_netdev}
    
    # Test mount
    echo "Testing NFS mount..."
    sudo mount -t nfs $NAS_IP:$SHARE_PATH $MOUNT_POINT
    
    if [ $? -eq 0 ]; then
        echo "NFS mount successful!"
        sudo umount $MOUNT_POINT
        
        # Add to fstab
        FSTAB_ENTRY="$NAS_IP:$SHARE_PATH $MOUNT_POINT nfs $NFS_OPTS 0 0"
        echo "$FSTAB_ENTRY" | sudo tee -a /etc/fstab
        echo "Added to /etc/fstab"
        
        # Mount permanently
        sudo mount -a
        echo "NAS mounted at $MOUNT_POINT"
    else
        echo "ERROR: NFS mount failed. Check NAS IP and share path."
        exit 1
    fi
    
elif [ "$PROTOCOL" = "2" ]; then
    # SMB/CIFS Setup
    echo "Setting up SMB/CIFS mount..."
    sudo apt install -y cifs-utils
    
    read -p "Enter SMB username: " SMB_USER
    read -sp "Enter SMB password: " SMB_PASS
    echo ""
    
    read -p "Enter SMB domain (optional, press Enter to skip): " SMB_DOMAIN
    
    # Create credentials file
    CRED_FILE="/etc/smb-credentials"
    if [ -n "$SMB_DOMAIN" ]; then
        echo "username=$SMB_DOMAIN\\$SMB_USER" | sudo tee $CRED_FILE
    else
        echo "username=$SMB_USER" | sudo tee $CRED_FILE
    fi
    echo "password=$SMB_PASS" | sudo tee -a $CRED_FILE
    sudo chmod 600 $CRED_FILE
    
    # Test mount
    echo "Testing SMB mount..."
    if [ -n "$SMB_DOMAIN" ]; then
        sudo mount -t cifs //$NAS_IP/$SHARE_PATH $MOUNT_POINT -o credentials=$CRED_FILE,uid=1000,gid=1000
    else
        sudo mount -t cifs //$NAS_IP/$SHARE_PATH $MOUNT_POINT -o credentials=$CRED_FILE,uid=1000,gid=1000
    fi
    
    if [ $? -eq 0 ]; then
        echo "SMB mount successful!"
        sudo umount $MOUNT_POINT
        
        # Add to fstab
        FSTAB_ENTRY="//$NAS_IP/$SHARE_PATH $MOUNT_POINT cifs credentials=$CRED_FILE,uid=1000,gid=1000,_netdev 0 0"
        echo "$FSTAB_ENTRY" | sudo tee -a /etc/fstab
        echo "Added to /etc/fstab"
        
        # Mount permanently
        sudo mount -a
        echo "NAS mounted at $MOUNT_POINT"
    else
        echo "ERROR: SMB mount failed. Check credentials and share path."
        exit 1
    fi
else
    echo "ERROR: Invalid protocol choice"
    exit 1
fi

# Create data directories
echo ""
echo "Creating data directories on NAS..."
sudo mkdir -p $MOUNT_POINT/{postgres,redis,qdrant,prometheus,grafana,logs,backups/vm-snapshots}
sudo chown -R $USER:$USER $MOUNT_POINT

echo ""
echo "=========================================="
echo "NAS setup completed!"
echo "=========================================="
echo "Mount point: $MOUNT_POINT"
echo "Directories created:"
ls -la $MOUNT_POINT
