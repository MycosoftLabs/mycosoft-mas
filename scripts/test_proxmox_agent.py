#!/usr/bin/env python3
"""Test Proxmox QEMU Guest Agent"""
import requests
import urllib3
import json
urllib3.disable_warnings()

PROXMOX_HOST = "https://192.168.0.202:8006"
headers = {"Authorization": "PVEAPIToken=myca@pve!mas=ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"}
VM_ID = 103
NODE = "pve"

# Check VM status
print("=== VM Status ===")
r = requests.get(f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/status/current", headers=headers, verify=False, timeout=10)
if r.ok:
    data = r.json()["data"]
    print(f"Status: {data.get('status')}")
    print(f"Name: {data.get('name')}")
    print(f"Agent: {data.get('agent', 'not configured')}")
else:
    print(f"Error: {r.status_code}")

# Check agent
print("\n=== Agent Info ===")
r2 = requests.get(f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/info", headers=headers, verify=False, timeout=10)
print(f"Status Code: {r2.status_code}")
if r2.ok:
    print(f"Agent OK: {json.dumps(r2.json(), indent=2)}")
else:
    print(f"Agent Error: {r2.text[:300]}")

# Try exec with correct format
print("\n=== Test Exec ===")
# The Proxmox API requires command as an array for exec
data = {
    "command": "/bin/echo",
    "input-data": ""
}
r3 = requests.post(
    f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec",
    headers=headers,
    data=data,
    verify=False,
    timeout=10
)
print(f"Exec Status: {r3.status_code}")
print(f"Exec Response: {r3.text[:300]}")
