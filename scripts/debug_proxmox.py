#!/usr/bin/env python3
"""Debug Proxmox connectivity and auth issues."""

import socket
import requests
import urllib3
urllib3.disable_warnings()

PROXMOX_IP = '192.168.0.90'

print("=" * 60)
print(f"  PROXMOX DEBUG - {PROXMOX_IP}")
print("=" * 60)

# Check which ports are open
ports_to_check = [22, 80, 443, 8006, 3128]
print("\n1. PORT SCAN:")
for port in ports_to_check:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((PROXMOX_IP, port))
        sock.close()
        status = "OPEN" if result == 0 else "CLOSED"
        print(f"   Port {port}: {status}")
    except Exception as e:
        print(f"   Port {port}: Error - {e}")

# Check Proxmox web interface
print("\n2. PROXMOX WEB INTERFACE:")
try:
    r = requests.get(f"https://{PROXMOX_IP}:8006/", verify=False, timeout=10)
    print(f"   Status: {r.status_code}")
    if "PVE" in r.text or "Proxmox" in r.text:
        print("   Content: Proxmox login page detected")
    else:
        print(f"   Content: {r.text[:200]}")
except Exception as e:
    print(f"   Error: {e}")

# Check API endpoint
print("\n3. API ENDPOINT CHECK:")
try:
    r = requests.get(f"https://{PROXMOX_IP}:8006/api2/json/version", verify=False, timeout=10)
    print(f"   /api2/json/version: {r.status_code}")
    if r.status_code == 200:
        print(f"   Response: {r.json()}")
except Exception as e:
    print(f"   Error: {e}")

# Try authentication with different formats
print("\n4. AUTHENTICATION ATTEMPTS:")
credentials = [
    ("root@pam", "20202020"),
    ("root", "20202020"),
    ("root@pve", "20202020"),
]

for username, password in credentials:
    try:
        r = requests.post(
            f"https://{PROXMOX_IP}:8006/api2/json/access/ticket",
            data={"username": username, "password": password},
            verify=False,
            timeout=10
        )
        print(f"   {username}: Status {r.status_code}")
        if r.status_code == 200:
            print(f"      => SUCCESS! Got ticket")
            data = r.json()
            print(f"      Username confirmed: {data.get('data', {}).get('username')}")
        elif r.status_code == 401:
            print(f"      => Authentication failed")
            # Check if there's more info in response
            try:
                error_data = r.json()
                if error_data:
                    print(f"      Response: {error_data}")
            except:
                pass
        elif r.status_code == 500:
            print(f"      => Server error - PAM might be misconfigured")
        else:
            print(f"      => Unexpected response: {r.text[:100]}")
    except requests.exceptions.Timeout:
        print(f"   {username}: TIMEOUT")
    except Exception as e:
        print(f"   {username}: Error - {e}")

# Check if there's a different Proxmox instance
print("\n5. SCANNING FOR OTHER PROXMOX INSTANCES:")
for last_octet in [2, 90, 100, 202, 203, 204]:
    ip = f"192.168.0.{last_octet}"
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((ip, 8006))
        sock.close()
        if result == 0:
            print(f"   {ip}:8006 - OPEN (Proxmox?)")
            # Quick auth test
            try:
                r = requests.post(
                    f"https://{ip}:8006/api2/json/access/ticket",
                    data={"username": "root@pam", "password": "20202020"},
                    verify=False,
                    timeout=5
                )
                if r.status_code == 200:
                    print(f"      => AUTH SUCCESS on {ip}!")
            except:
                pass
    except:
        pass

print("\n" + "=" * 60)
