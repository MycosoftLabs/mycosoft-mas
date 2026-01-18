#!/usr/bin/env python3
"""Test QEMU Guest Agent exec with various commands"""
import requests
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROXMOX_HOST = "https://192.168.0.202:8006"
TOKEN_ID = "myca@pve!mas"
TOKEN_SECRET = "ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"
headers = {"Authorization": f"PVEAPIToken={TOKEN_ID}={TOKEN_SECRET}"}

def test_exec(cmd):
    url = f"{PROXMOX_HOST}/api2/json/nodes/pve/qemu/103/agent/exec"
    r = requests.post(url, headers=headers, data={"command": cmd}, verify=False, timeout=30)
    print(f"{cmd}: {r.status_code}", end="")
    if r.status_code == 200:
        pid = r.json().get("data", {}).get("pid")
        time.sleep(2)
        url2 = f"{PROXMOX_HOST}/api2/json/nodes/pve/qemu/103/agent/exec-status"
        r2 = requests.get(url2, headers=headers, params={"pid": pid}, verify=False, timeout=30)
        if r2.ok:
            data = r2.json().get("data", {})
            exitcode = data.get("exitcode", "N/A")
            output = data.get("out-data", "")[:50]
            print(f" -> exit={exitcode} out={output}")
        else:
            print(f" -> status check failed")
    else:
        print(f" -> ERROR: {r.text[:80]}")

print("Testing QEMU Guest Agent exec commands...")
print()

# Test various commands
commands = [
    "/bin/id",
    "/bin/pwd",
    "/bin/ls",
    "/bin/whoami",
    "/bin/hostname",
    "/usr/bin/docker",
    "/usr/bin/git",
    "/bin/cat /etc/os-release",
    "/bin/bash -c pwd",
]

for cmd in commands:
    test_exec(cmd)
