#!/usr/bin/env python3
"""Test Proxmox exec and get result"""
import requests
import urllib3
import time
import base64

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROXMOX_HOST = "https://192.168.0.202:8006"
PROXMOX_TOKEN_ID = os.environ.get("PROXMOX_TOKEN_ID", "myca@pve!mas")
PROXMOX_TOKEN_SECRET = os.environ.get("PROXMOX_TOKEN_SECRET", "")
VM_ID = 103
NODE = "pve"

headers = {
    "Authorization": f"PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}"
}

url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec"

# Run hostname
print("Running: /bin/hostname")
resp = requests.post(url, headers=headers, data={"command": "/bin/hostname"}, verify=False)
print(f"Status: {resp.status_code}, Response: {resp.json()}")
pid = resp.json().get("data", {}).get("pid")

if pid:
    time.sleep(2)
    status_url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec-status"
    status = requests.get(status_url, headers=headers, params={"pid": pid}, verify=False)
    data = status.json().get("data", {})
    print(f"Exec status: {data}")
    
    # Decode output
    out = data.get("out-data", "")
    if out:
        try:
            decoded = base64.b64decode(out).decode()
            print(f"Decoded output: {decoded}")
        except Exception:
            print(f"Raw output: {out}")

# Try bash -c style via input-data
print("\n\nRunning: bash -c 'docker ps'")
resp = requests.post(url, headers=headers, data={
    "command": "/bin/bash -c 'docker ps'"
}, verify=False)
print(f"Status: {resp.status_code}")
if resp.ok:
    pid = resp.json().get("data", {}).get("pid")
    if pid:
        time.sleep(3)
        status = requests.get(status_url, headers=headers, params={"pid": pid}, verify=False)
        data = status.json().get("data", {})
        print(f"Exec status: exited={data.get('exited')}, exitcode={data.get('exitcode')}")
        out = data.get("out-data", "")
        if out:
            try:
                decoded = base64.b64decode(out).decode()
                print(f"Output:\n{decoded}")
            except Exception:
                print(f"Raw: {out}")
else:
    print(f"Error: {resp.text[:300]}")
