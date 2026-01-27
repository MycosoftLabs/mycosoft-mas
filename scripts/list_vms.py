#!/usr/bin/env python3
"""List all VMs on Proxmox"""
import requests
import urllib3
urllib3.disable_warnings()

PROXMOX = "https://192.168.0.202:8006"
TOKEN = "root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"
headers = {"Authorization": f"PVEAPIToken={TOKEN}"}

r = requests.get(f"{PROXMOX}/api2/json/nodes/pve/qemu", headers=headers, verify=False, timeout=5)
vms = r.json().get("data", [])

print("=== Proxmox VMs ===")
for vm in sorted(vms, key=lambda x: x.get("vmid", 0)):
    vmid = vm.get("vmid")
    name = vm.get("name", "unknown")
    status = vm.get("status", "unknown")
    print(f"  VM {vmid}: {name} - {status}")
