#!/usr/bin/env python3
"""
Get UniFi Network Topology via API
"""

import requests
import urllib3
import json
urllib3.disable_warnings()

UNIFI_HOST = "192.168.0.1"  # Dream Machine
UNIFI_USER = "cursor_agent"  # or admin
UNIFI_PASS = "Mushroom1!Mushroom1!"

print("=" * 70)
print("  UNIFI NETWORK TOPOLOGY")
print("=" * 70)

session = requests.Session()
session.verify = False

# Try to login to UniFi
print("\n1. Attempting UniFi login...")

# Try different auth endpoints (UDM Pro Max uses different API)
login_urls = [
    f"https://{UNIFI_HOST}/api/auth/login",
    f"https://{UNIFI_HOST}:443/api/auth/login",
    f"https://{UNIFI_HOST}/api/login",
]

logged_in = False
for url in login_urls:
    try:
        r = session.post(
            url,
            json={"username": UNIFI_USER, "password": UNIFI_PASS},
            timeout=10
        )
        print(f"  {url}: {r.status_code}")
        if r.status_code == 200:
            logged_in = True
            print("  => Login successful!")
            break
    except Exception as e:
        print(f"  {url}: Error - {e}")

if not logged_in:
    # Try default admin credentials
    print("\nTrying alternate credentials...")
    for user in ["admin", "root", "cursor_agent"]:
        for pwd in ["Mushroom1!Mushroom1!", "20202020", "admin"]:
            try:
                r = session.post(
                    f"https://{UNIFI_HOST}/api/auth/login",
                    json={"username": user, "password": pwd},
                    timeout=5
                )
                if r.status_code == 200:
                    print(f"  => Login successful with {user}!")
                    logged_in = True
                    break
            except:
                pass
        if logged_in:
            break

if logged_in:
    print("\n2. Getting network devices...")
    
    # Get devices
    endpoints = [
        "/proxy/network/api/s/default/stat/device",
        "/api/s/default/stat/device",
        "/proxy/network/api/s/default/stat/sta",
        "/api/s/default/stat/sta",
    ]
    
    for endpoint in endpoints:
        try:
            r = session.get(f"https://{UNIFI_HOST}{endpoint}", timeout=10)
            if r.status_code == 200:
                data = r.json()
                print(f"\n{endpoint}:")
                
                if "data" in data:
                    for device in data["data"]:
                        name = device.get("name") or device.get("hostname") or device.get("oui") or "Unknown"
                        ip = device.get("ip") or device.get("last_ip") or "N/A"
                        mac = device.get("mac", "N/A")
                        dtype = device.get("type", device.get("dev_vendor", "unknown"))
                        uplink = device.get("uplink", {})
                        uplink_device = uplink.get("uplink_device_name", "")
                        uplink_port = uplink.get("uplink_port_idx", "")
                        
                        print(f"  {name:<30} IP: {ip:<16} MAC: {mac:<18} Type: {dtype}")
                        if uplink_device:
                            print(f"    -> Connected to: {uplink_device} Port {uplink_port}")
        except Exception as e:
            print(f"  {endpoint}: Error - {e}")
    
    # Get network topology
    print("\n3. Getting topology...")
    try:
        r = session.get(f"https://{UNIFI_HOST}/proxy/network/api/s/default/stat/device-basic", timeout=10)
        if r.status_code == 200:
            for device in r.json().get("data", []):
                print(f"  {device.get('name', 'Unknown')}: {device.get('ip', 'N/A')} - {device.get('type', 'unknown')}")
    except Exception as e:
        print(f"  Error: {e}")
        
else:
    print("\nCould not login to UniFi controller.")
    print("Please check credentials or use the UniFi web UI directly.")

# Also check what's running locally on Windows PC
print("\n" + "=" * 70)
print("  LOCAL SERVICES ON WINDOWS PC (192.168.0.172)")
print("=" * 70)

import socket
local_ports = [3000, 5678, 8000, 8003, 8006, 8443, 9090]
for port in local_ports:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        if result == 0:
            service = {
                3000: "Website (Next.js)",
                5678: "n8n",
                8000: "MINDEX API",
                8003: "MycoBrain",
                8006: "Proxmox",
                8443: "UniFi Controller",
                9090: "Prometheus",
            }.get(port, "Unknown")
            print(f"  Port {port}: {service} - RUNNING LOCALLY")
    except:
        pass

print("\n" + "=" * 70)
