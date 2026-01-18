#!/bin/bash
# VM2 (Code Operator) Setup Script
# Run this on VM2 after Ubuntu Desktop installation

set -e

echo "=========================================="
echo "VM2 Code Operator Setup"
echo "=========================================="

# Install base tools (same as VM1)
echo "[1/6] Installing base tools..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git vim htop net-tools jq

# Install VS Code
echo "[2/6] Installing VS Code..."
if ! command -v code &> /dev/null; then
    wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg
    sudo install -o root -g root -m 644 packages.microsoft.gpg /etc/apt/trusted.gpg.d/
    sudo sh -c 'echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/trusted.gpg.d/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list'
    sudo apt update
    sudo apt install -y code
    rm packages.microsoft.gpg
    echo "VS Code installed"
else
    echo "VS Code already installed"
fi

# Install Cursor IDE (if available)
echo "[3/6] Installing Cursor IDE..."
if [ ! -f /usr/bin/cursor ]; then
    CURSOR_URL=$(curl -s https://api.github.com/repos/getcursor/cursor/releases/latest | grep "browser_download_url.*amd64.deb" | cut -d '"' -f 4)
    if [ -n "$CURSOR_URL" ]; then
        wget -O /tmp/cursor.deb "$CURSOR_URL"
        sudo dpkg -i /tmp/cursor.deb || sudo apt install -f -y
        rm /tmp/cursor.deb
        echo "Cursor IDE installed"
    else
        echo "WARNING: Could not download Cursor IDE. Install manually from https://cursor.sh"
    fi
else
    echo "Cursor IDE already installed"
fi

# Install Node.js and Python (for development)
echo "[4/6] Installing development tools..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs python3.11 python3.11-venv python3-pip

# Install Docker (for local testing)
echo "[5/6] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "Docker installed"
else
    echo "Docker already installed"
fi

# Configure access to VM1
echo "[6/6] Configuring access to VM1..."
read -p "Enter VM1 IP address (default: 192.168.1.100): " VM1_IP
VM1_IP=${VM1_IP:-192.168.1.100}

# Add VM1 to /etc/hosts
if ! grep -q "mycosoft-production" /etc/hosts; then
    echo "$VM1_IP mycosoft-production" | sudo tee -a /etc/hosts
    echo "Added mycosoft-production to /etc/hosts"
fi

# Test connectivity
echo ""
echo "Testing connectivity to VM1..."
if ping -c 1 $VM1_IP > /dev/null 2>&1; then
    echo "✅ VM1 is reachable"
    
    # Test service endpoints
    echo "Testing service endpoints..."
    curl -sf http://$VM1_IP:8001/health > /dev/null && echo "✅ MAS Orchestrator: Accessible" || echo "❌ MAS Orchestrator: Not accessible"
    curl -sf http://$VM1_IP:3000 > /dev/null && echo "✅ Website: Accessible" || echo "❌ Website: Not accessible"
else
    echo "❌ VM1 is not reachable. Check network configuration."
fi

# Create workspace
mkdir -p ~/mycosoft-dev
cd ~/mycosoft-dev

echo ""
echo "=========================================="
echo "VM2 Setup Completed!"
echo "=========================================="
echo ""
echo "Installed tools:"
echo "  - VS Code: $(code --version 2>/dev/null | head -1 || echo 'installed')"
echo "  - Cursor IDE: $(cursor --version 2>/dev/null || echo 'installed')"
echo "  - Node.js: $(node --version)"
echo "  - Python: $(python3.11 --version)"
echo "  - Docker: $(docker --version)"
echo ""
echo "VM1 access configured:"
echo "  - Hostname: mycosoft-production"
echo "  - IP: $VM1_IP"
echo ""
echo "Workspace: ~/mycosoft-dev"
echo ""
echo "Next steps:"
echo "  1. Clone repositories for local development"
echo "  2. Configure VS Code/Cursor to connect to VM1 services"
echo "  3. Install development extensions"
