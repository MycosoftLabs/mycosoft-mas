#!/bin/bash
# Network Configuration Script
# Run this on VM1 and VM2 to configure static IPs

set -e

echo "=========================================="
echo "Network Configuration"
echo "=========================================="

# Detect network interface
INTERFACE=$(ip route | grep default | awk '{print $5}' | head -1)

if [ -z "$INTERFACE" ]; then
    echo "ERROR: Could not detect network interface"
    exit 1
fi

echo "Detected interface: $INTERFACE"
echo ""

# Get current IP info
CURRENT_IP=$(ip -4 addr show $INTERFACE | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
echo "Current IP: $CURRENT_IP"
echo ""

# Prompt for configuration
read -p "Enter static IP address (e.g., 192.168.1.100): " STATIC_IP
read -p "Enter subnet mask (e.g., 24): " SUBNET
read -p "Enter gateway IP (e.g., 192.168.1.1): " GATEWAY
read -p "Enter DNS server 1 (default: 1.1.1.1): " DNS1
DNS1=${DNS1:-1.1.1.1}
read -p "Enter DNS server 2 (default: 8.8.8.8): " DNS2
DNS2=${DNS2:-8.8.8.8}

# Backup existing netplan config
sudo cp /etc/netplan/*.yaml /etc/netplan/*.yaml.backup 2>/dev/null || true

# Create netplan config
NETPLAN_FILE="/etc/netplan/00-mycosoft-static.yaml"
sudo tee $NETPLAN_FILE > /dev/null <<EOF
network:
  version: 2
  renderer: networkd
  ethernets:
    $INTERFACE:
      dhcp4: false
      addresses:
        - $STATIC_IP/$SUBNET
      routes:
        - to: default
          via: $GATEWAY
      nameservers:
        addresses:
          - $DNS1
          - $DNS2
          - $GATEWAY
EOF

echo ""
echo "Netplan configuration created: $NETPLAN_FILE"
echo ""
read -p "Apply network configuration now? (y/n): " APPLY

if [ "$APPLY" = "y" ]; then
    echo "Applying network configuration..."
    sudo netplan apply
    echo ""
    echo "Network configuration applied!"
    echo "New IP: $STATIC_IP"
    echo ""
    echo "NOTE: If you lose connection, check the configuration and restore from backup:"
    echo "  sudo cp /etc/netplan/*.yaml.backup /etc/netplan/00-installer-config.yaml"
    echo "  sudo netplan apply"
else
    echo ""
    echo "Configuration saved. Apply manually with:"
    echo "  sudo netplan apply"
fi
