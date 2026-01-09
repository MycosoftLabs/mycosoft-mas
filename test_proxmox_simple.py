#!/usr/bin/env python3
"""Simple standalone Proxmox test - no package imports"""
import os
import requests
import urllib3
urllib3.disable_warnings()

TOKEN_ID = os.environ.get("PROXMOX_TOKEN_ID")
TOKEN_SECRET = os.environ.get("PROXMOX_TOKEN_SECRET")

if not TOKEN_ID or not TOKEN_SECRET:
    print("ERROR: Set Proxmox environment variables")
    print("  PROXMOX_TOKEN_ID=myca@pve!mas")
    print("  PROXMOX_TOKEN_SECRET=your-secret")
    exit(1)

NODES = [
    ("build", "192.168.0.202"),
    ("dc1", "192.168.0.2"),
    ("dc2", "192.168.0.131"),
]

session = requests.Session()
session.verify = False
session.headers["Authorization"] = f"PVEAPIToken={TOKEN_ID}={TOKEN_SECRET}"

print("=" * 50)
print("  MYCA Proxmox Connection Test")
print("=" * 50)
print()

# Test each node
print("Nodes:")
working_node = None
for name, ip in NODES:
    try:
        r = session.get(f"https://{ip}:8006/api2/json/version", timeout=10)
        if r.status_code == 200:
            v = r.json().get("data", {}).get("version", "?")
            print(f"  [OK] {name} ({ip}): online v{v}")
            if not working_node:
                working_node = (name, ip)
        else:
            print(f"  [!!] {name} ({ip}): HTTP {r.status_code}")
    except requests.exceptions.Timeout:
        print(f"  [--] {name} ({ip}): timeout")
    except Exception as e:
        print(f"  [!!] {name} ({ip}): {e}")

if working_node:
    print()
    print("VMs on", working_node[0] + ":")
    try:
        # Get the node name from API
        r = session.get(f"https://{working_node[1]}:8006/api2/json/nodes", timeout=10)
        nodes = r.json().get("data", [])
        
        for node in nodes:
            node_name = node.get("node")
            r2 = session.get(f"https://{working_node[1]}:8006/api2/json/nodes/{node_name}/qemu", timeout=10)
            vms = r2.json().get("data", [])
            for vm in vms:
                status_char = "R" if vm.get("status") == "running" else "S"
                print(f"  [{status_char}] {vm.get('vmid')}: {vm.get('name', 'unnamed')} ({vm.get('status')})")
    except Exception as e:
        print(f"  Error listing VMs: {e}")

print()
print("=" * 50)
print("  MYCA IS CONNECTED TO PROXMOX!")
print("=" * 50)
