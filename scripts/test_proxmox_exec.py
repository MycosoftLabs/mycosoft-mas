#!/usr/bin/env python3
"""Test Proxmox exec API format"""
import requests
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROXMOX_HOST = "https://192.168.0.202:8006"
PROXMOX_TOKEN_ID = "myca@pve!mas"
PROXMOX_TOKEN_SECRET = "ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"
VM_ID = 103
NODE = "pve"

headers = {
    "Authorization": f"PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}"
}

# Test 1: Simple command with path
print("=== Test 1: path=/bin/hostname ===")
url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec"
resp = requests.post(url, headers=headers, data={"path": "/bin/hostname"}, verify=False)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:300]}")

if resp.ok:
    pid = resp.json().get("data", {}).get("pid")
    if pid:
        time.sleep(2)
        status_url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec-status"
        status = requests.get(status_url, headers=headers, params={"pid": pid}, verify=False)
        print(f"Status: {status.json()}")

# Test 2: bash -c with args
print("\n=== Test 2: path=/bin/bash with args ===")
resp = requests.post(url, headers=headers, data={
    "path": "/bin/bash",
    "arg": "-c",
    "arg": "echo hello"
}, verify=False)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:300]}")

# Test 3: Using command parameter
print("\n=== Test 3: command=/bin/hostname ===")
resp = requests.post(url, headers=headers, data={"command": "/bin/hostname"}, verify=False)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:300]}")
