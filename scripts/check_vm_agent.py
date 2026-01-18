#!/usr/bin/env python3
"""Check QEMU Guest Agent status on VM 103"""
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROXMOX_HOST = "https://192.168.0.202:8006"
PROXMOX_TOKEN_ID = "myca@pve!mas"
PROXMOX_TOKEN_SECRET = "ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"
VM_ID = 103
NODE = "pve"

headers = {
    "Authorization": f"PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}"
}

# Check VM config
print("=== VM 103 Configuration ===")
url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/config"
resp = requests.get(url, headers=headers, verify=False)
if resp.ok:
    config = resp.json().get("data", {})
    print(f"  Agent enabled: {config.get('agent', 'NOT SET')}")
    print(f"  OS Type: {config.get('ostype', 'unknown')}")
else:
    print(f"  Error: {resp.status_code}")

# Try agent ping
print("\n=== Testing Agent Ping ===")
url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/ping"
resp = requests.post(url, headers=headers, verify=False)
print(f"  Status: {resp.status_code}")
if resp.ok:
    print(f"  Response: {resp.json()}")
else:
    print(f"  Error: {resp.text[:200]}")

# Try agent info
print("\n=== Agent Info ===")
url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/info"
resp = requests.get(url, headers=headers, verify=False)
print(f"  Status: {resp.status_code}")
if resp.ok:
    print(f"  Response: {resp.json()}")
else:
    print(f"  Error: {resp.text[:200]}")
