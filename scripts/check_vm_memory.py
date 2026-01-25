#!/usr/bin/env python3
"""Check VM memory and find what's using it"""
import requests
import urllib3
urllib3.disable_warnings()

PROXMOX_HOST = "https://192.168.0.202:8006"
headers = {"Authorization": "PVEAPIToken=myca@pve!mas=ca23b6c8-5746-46c4-8e36-fc6caad5a9e5"}
VM_ID = 103
NODE = "pve"

def exec_cmd(cmd, timeout=30):
    """Execute command via QEMU Guest Agent"""
    url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec"
    import time
    try:
        data = {"command": "/bin/bash", "input-data": cmd}
        r = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
        if not r.ok:
            return None, f"Failed: {r.status_code}"
        pid = r.json().get("data", {}).get("pid")
        if not pid:
            return None, "No PID"
        
        status_url = f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/agent/exec-status"
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(1)
            s = requests.get(status_url, headers=headers, params={"pid": pid}, verify=False, timeout=5)
            if s.ok:
                data = s.json().get("data", {})
                if data.get("exited"):
                    return data.get("exitcode", 0), data.get("out-data", "")
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

print("=== VM 103 Memory Check ===\n")

# Get VM status from Proxmox
r = requests.get(f"{PROXMOX_HOST}/api2/json/nodes/{NODE}/qemu/{VM_ID}/status/current", headers=headers, verify=False, timeout=10)
if r.ok:
    data = r.json()["data"]
    mem = data.get("mem", 0)
    maxmem = data.get("maxmem", 1)
    cpu = data.get("cpu", 0)
    print(f"Proxmox View:")
    print(f"  Memory: {mem / 1024**3:.1f} GB / {maxmem / 1024**3:.1f} GB ({100*mem/maxmem:.1f}%)")
    print(f"  CPU: {cpu*100:.1f}%")
    print(f"  Status: {data.get('status')}")

print("\n=== Top Memory Consumers ===")
code, out = exec_cmd("ps aux --sort=-%mem | head -20")
if code == 0:
    print(out)
else:
    print(f"Error: {out}")

print("\n=== Docker Container Memory ===")
code, out = exec_cmd("docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}'")
if code == 0:
    print(out)
else:
    print(f"Error: {out}")

print("\n=== Free Memory ===")
code, out = exec_cmd("free -h")
if code == 0:
    print(out)
else:
    print(f"Error: {out}")
