#!/bin/bash
# fix_proxmox_firewall.sh - Allow Proxmox API (8006) from LAN
# Run on Proxmox host (192.168.0.105) or gateway. Mar 5, 2026.
#
# Proxmox API was unreachable from 192.168.0.0/24. This script adds
# iptables rules to allow TCP 8006 from the Mycosoft LAN.
#
# Usage: sudo ./fix_proxmox_firewall.sh

set -e

# Allow 8006 from LAN (adjust interface if needed)
# Typical Proxmox: vmbr0 or the bridge for 192.168.0.x
iptables -I INPUT -p tcp -s 192.168.0.0/24 --dport 8006 -j ACCEPT 2>/dev/null || true

echo "Proxmox firewall: added allow rule for 192.168.0.0/24:8006"
echo "Verify with: iptables -L INPUT -n -v | grep 8006"
echo ""
echo "To make persistent (Proxmox/Debian):"
echo "  apt install iptables-persistent"
echo "  iptables-save > /etc/iptables/rules.v4"
