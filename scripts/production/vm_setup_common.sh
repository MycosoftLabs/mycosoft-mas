#!/bin/bash
# Common setup script for all MYCA production VMs
# Run this after VM creation via SSH

set -e

echo "=================================================="
echo "  MYCA VM Initial Setup"
echo "=================================================="

# Update system
echo "[1/8] Updating system packages..."
apt update && apt upgrade -y

# Install common packages
echo "[2/8] Installing common packages..."
apt install -y \
    curl \
    wget \
    git \
    vim \
    htop \
    net-tools \
    nfs-common \
    jq \
    unzip \
    ca-certificates \
    gnupg \
    lsb-release

# Install Docker
echo "[3/8] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker $SUDO_USER 2>/dev/null || true
fi

# Install Docker Compose
echo "[4/8] Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    apt install -y docker-compose-plugin
fi

# Create myca user if not exists
echo "[5/8] Creating myca user..."
if ! id "myca" &>/dev/null; then
    useradd -m -s /bin/bash -G sudo,docker myca
    echo "myca:$(openssl rand -base64 32)" | chpasswd
    echo "Created myca user with random password"
fi

# Create NAS mount point
echo "[6/8] Setting up NAS mount..."
mkdir -p /mnt/mycosoft

# Add NAS mount to fstab (commented out - uncomment after verifying NAS IP)
if ! grep -q "mycosoft" /etc/fstab; then
    echo "# MYCA NAS Mount - uncomment after verifying" >> /etc/fstab
    echo "# 192.168.0.1:/mycosoft /mnt/mycosoft nfs4 defaults,_netdev,noatime 0 0" >> /etc/fstab
    echo "NAS mount entry added to /etc/fstab (commented)"
fi

# Create standard directories
echo "[7/8] Creating standard directories..."
mkdir -p /opt/myca
mkdir -p /var/log/myca
mkdir -p /etc/myca
chown -R myca:myca /opt/myca /var/log/myca /etc/myca

# Install Node.js (for website VM)
echo "[8/8] Installing Node.js 20..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt install -y nodejs
fi

# Install PM2 globally
npm install -g pm2

# Summary
echo ""
echo "=================================================="
echo "  Setup Complete!"
echo "=================================================="
echo ""
echo "  Next steps:"
echo "  1. Edit /etc/fstab and uncomment NAS mount"
echo "  2. Run: mount -a"
echo "  3. Verify NAS access: ls /mnt/mycosoft"
echo "  4. Clone MYCA repo: git clone https://github.com/MycosoftLabs/mycosoft-mas.git /opt/myca"
echo "  5. Run VM-specific setup script"
echo ""
