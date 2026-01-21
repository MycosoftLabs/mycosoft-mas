#!/usr/bin/env python3
import requests, urllib3
urllib3.disable_warnings()
headers = {"Authorization": "PVEAPIToken=myca@pve!mas=ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"}
PROXMOX = "https://192.168.0.202:8006"

# Get status
r = requests.get(f"{PROXMOX}/api2/json/nodes/pve/qemu/103/status/current", headers=headers, verify=False, timeout=10)
if r.ok:
    data = r.json()["data"]
    print(f"VM Status: {data.get('status')}")
    print(f"Agent: {data.get('agent')}")
    print(f"QMPstatus: {data.get('qmpstatus')}")
    
    if data.get("status") != "running":
        print("\nStarting VM 103...")
        r2 = requests.post(f"{PROXMOX}/api2/json/nodes/pve/qemu/103/status/start", headers=headers, verify=False, timeout=10)
        print(f"Start result: {r2.status_code} - {r2.text[:100]}")
else:
    print(f"Error: {r.status_code} - {r.text[:100]}")
