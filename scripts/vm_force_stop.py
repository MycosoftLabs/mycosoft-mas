#!/usr/bin/env python3
"""Force stop VM 103"""
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROXMOX_HOST = "https://192.168.0.202:8006"
PROXMOX_TOKEN_ID = "myca@pve!mas"
PROXMOX_TOKEN_SECRET = "ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"
headers = {"Authorization": f"PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}"}

print("Force stopping VM 103...")
resp = requests.post(f"{PROXMOX_HOST}/api2/json/nodes/pve/qemu/103/status/stop", 
                     headers=headers, verify=False)
print(f"Response: {resp.status_code} - {resp.text[:200]}")
