#!/bin/bash
# VM 103 Post-Installation Setup Script
# Run this on the Ubuntu VM after first login

set -e

echo "=== Mycosoft VM Setup Script ==="
echo "Installing essential packages..."

# Update system
sudo apt update

# Install SSH Server (critical for remote access)
sudo apt install -y openssh-server
sudo systemctl enable ssh
sudo systemctl start ssh

# Install QEMU Guest Agent (for Proxmox integration)
sudo apt install -y qemu-guest-agent
sudo systemctl enable qemu-guest-agent
sudo systemctl start qemu-guest-agent

# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install -y docker-compose-plugin

# Install essential tools
sudo apt install -y git curl wget htop net-tools

# Configure firewall (allow SSH and Docker ports)
sudo ufw allow ssh
sudo ufw allow 3000/tcp  # Mycosoft Website
sudo ufw allow 8000/tcp  # MINDEX API
sudo ufw allow 8003/tcp  # MycoBrain Service
sudo ufw --force enable

echo "=== Setup Complete ==="
echo "SSH is now available on port 22"
echo "Docker is installed - log out and back in for docker group"
echo "QEMU Guest Agent is running"
ip addr show | grep "inet " | grep -v 127.0.0.1

