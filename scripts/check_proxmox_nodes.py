#!/usr/bin/env python3
"""Check Proxmox nodes and VMs"""
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROXMOX_HOST = 'https://192.168.0.202:8006'
TOKEN_ID = 'myca@pve!mas'
TOKEN_SECRET = 'ca23b6c8-5746-46c4-8e36-fc6caad5a9e5'
headers = {'Authorization': f'PVEAPIToken={TOKEN_ID}={TOKEN_SECRET}'}

print("=" * 50)
print("  PROXMOX CLUSTER STATUS")
print("=" * 50)

# Get nodes
try:
    r = requests.get(f'{PROXMOX_HOST}/api2/json/nodes', headers=headers, verify=False, timeout=10)
    if r.ok:
        print("\nNodes:")
        for node in r.json().get('data', []):
            print(f"  - {node.get('node')}: {node.get('status')} (IP: {node.get('ip', 'N/A')})")
    else:
        print(f"Error: {r.status_code}")
except Exception as e:
    print(f"Connection error: {e}")

# Get cluster resources
try:
    r2 = requests.get(f'{PROXMOX_HOST}/api2/json/cluster/resources', headers=headers, verify=False, timeout=10)
    if r2.ok:
        print("\nVMs:")
        for item in r2.json().get('data', []):
            if item.get('type') == 'qemu':
                vmid = item.get('vmid')
                name = item.get('name', 'unnamed')
                status = item.get('status', 'unknown')
                node = item.get('node', 'unknown')
                print(f"  - VM {vmid}: {name} on {node} ({status})")
except Exception as e:
    print(f"Resources error: {e}")

print()
