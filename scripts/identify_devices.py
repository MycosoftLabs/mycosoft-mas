#!/usr/bin/env python3
"""Identify devices on network by checking ports."""

import socket
import subprocess

def scan_ports(ip, ports):
    """Scan ports on an IP."""
    open_ports = []
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((ip, port))
            sock.close()
            if result == 0:
                open_ports.append(port)
        except:
            pass
    return open_ports

# Common ports for identification
PORTS = [22, 80, 443, 3000, 3389, 5000, 5001, 5678, 8000, 8003, 8006, 8080, 8443, 9090]

# Port signatures
PORT_SIGNATURES = {
    8006: "Proxmox",
    8443: "UniFi Controller",
    5678: "n8n",
    3000: "Website/Next.js",
    8000: "MINDEX API",
    8003: "MycoBrain",
    5000: "NAS DSM",
    5001: "NAS DSM SSL",
    22: "SSH",
    80: "HTTP",
    443: "HTTPS",
    3389: "RDP (Windows)",
}

# Devices to check
devices = [
    "192.168.0.34",  # Web device from scan
    "192.168.0.68",  # Unknown
    "192.168.0.85",  # Unknown
    "192.168.0.90",  # Proxmox
    "192.168.0.120", # Unknown
    "192.168.0.163", # Unknown
    "192.168.0.183", # Could be VM
]

print("=" * 60)
print("  DEVICE IDENTIFICATION SCAN")
print("=" * 60)

for ip in devices:
    print(f"\n{ip}:")
    open_ports = scan_ports(ip, PORTS)
    if open_ports:
        signatures = []
        for port in open_ports:
            sig = PORT_SIGNATURES.get(port, f"Port {port}")
            signatures.append(f"  - Port {port}: {sig}")
        print("\n".join(signatures))
        
        # Determine device type
        if 8006 in open_ports:
            print("  => PROXMOX SERVER")
        elif 8443 in open_ports:
            print("  => UNIFI CONTROLLER (Dream Machine?)")
        elif 5678 in open_ports:
            print("  => n8n (MAS VM?)")
        elif 3000 in open_ports:
            print("  => Website Container (Sandbox VM?)")
        elif 5000 in open_ports or 5001 in open_ports:
            print("  => NAS")
        elif 3389 in open_ports:
            print("  => Windows Machine")
    else:
        print("  No common ports open (might be IoT/AP/Switch)")

print("\n" + "=" * 60)
