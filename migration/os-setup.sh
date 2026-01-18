#!/bin/bash
# Ubuntu 22.04 Base Setup Script
# Run this on VM1 and VM2 after Ubuntu installation

set -e

echo "=========================================="
echo "Mycosoft VM Base Setup"
echo "=========================================="

# Update system
echo "[1/10] Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install essential tools
echo "[2/10] Installing essential tools..."
sudo apt install -y curl wget git vim htop net-tools jq unzip

# Install Docker
echo "[3/10] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "Docker installed successfully"
else
    echo "Docker already installed"
fi

# Install Docker Compose
echo "[4/10] Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "Docker Compose installed successfully"
else
    echo "Docker Compose already installed"
fi

# Install Node.js 20
echo "[5/10] Installing Node.js 20..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y nodejs
    echo "Node.js $(node --version) installed"
else
    echo "Node.js already installed: $(node --version)"
fi

# Install Python 3.11
echo "[6/10] Installing Python 3.11..."
sudo apt install -y python3.11 python3.11-venv python3-pip python3.11-dev

# Install Poetry
echo "[7/10] Installing Poetry..."
if ! command -v poetry &> /dev/null; then
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    echo "Poetry installed successfully"
else
    echo "Poetry already installed"
fi

# Install Proxmox backup client
echo "[8/10] Installing Proxmox backup client..."
sudo apt install -y proxmox-backup-client

# Create workspace directory
echo "[9/10] Creating workspace directory..."
sudo mkdir -p /opt/mycosoft
sudo chown $USER:$USER /opt/mycosoft
mkdir -p /opt/mycosoft/{scripts,logs,docs}

# Install UFW firewall
echo "[10/10] Installing and configuring firewall..."
sudo apt install -y ufw
sudo ufw allow 22/tcp
sudo ufw --force enable

echo ""
echo "=========================================="
echo "Base setup completed!"
echo "=========================================="
echo ""
echo "Installed components:"
echo "  - Docker: $(docker --version)"
echo "  - Docker Compose: $(docker-compose --version)"
echo "  - Node.js: $(node --version)"
echo "  - Python: $(python3.11 --version)"
echo "  - Poetry: $(poetry --version 2>/dev/null || echo 'installed')"
echo ""
echo "Workspace: /opt/mycosoft"
echo ""
echo "Next steps:"
echo "  - Configure network (run network-setup.sh)"
echo "  - Setup NAS mount (run nas-setup.sh)"
echo "  - Transfer codebase"
