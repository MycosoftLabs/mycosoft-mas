#!/usr/bin/env python3
"""Test exec command formats"""
import requests
import urllib3
import time
import base64
urllib3.disable_warnings()

PROXMOX_HOST = "https://192.168.0.202:8006"
headers = {"Authorization": "PVEAPIToken=myca@pve!mas=ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"}
VM_ID = 103
NODE = "pve"

def test_exec(desc, command_data):
    print(f"\n=== {desc} ===")
    print(f"Data: {command_data}")
    r = requests.post(
        f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec",
        headers=headers,
        data=command_data,
        verify=False,
        timeout=10
    )
    print(f"Status: {r.status_code}")
    if not r.ok:
        print(f"Error: {r.text[:200]}")
        return
    
    pid = r.json().get("data", {}).get("pid")
    if not pid:
        print("No PID")
        return
    
    print(f"PID: {pid}")
    time.sleep(3)
    
    s = requests.get(
        f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec-status",
        headers=headers,
        params={"pid": pid},
        verify=False,
        timeout=10
    )
    if s.ok:
        data = s.json().get("data", {})
        print(f"Exited: {data.get('exited')}")
        print(f"Exit Code: {data.get('exitcode')}")
        out = data.get("out-data", "")
        if out:
            # Try base64 decode
            try:
                decoded = base64.b64decode(out).decode()
                print(f"Output (b64): {decoded[:200]}")
            except:
                print(f"Output: {out[:200]}")
        err = data.get("err-data", "")
        if err:
            print(f"Stderr: {err[:100]}")

# Test 1: Simple command
test_exec("Simple /bin/echo", {"command": "/bin/echo hello"})

# Test 2: Bash with -c
test_exec("Bash -c echo", {"command": "/bin/bash", "input-data": "echo hello world"})

# Test 3: Hostname
test_exec("Hostname", {"command": "/bin/hostname"})

# Test 4: Docker ps
test_exec("Docker ps", {"command": "/usr/bin/docker ps --format {{.Names}}"})
