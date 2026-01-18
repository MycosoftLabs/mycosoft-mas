#!/usr/bin/env python3
"""Detailed Proxmox API test"""
import requests
import urllib3
import json
urllib3.disable_warnings()

TOKEN_ID = "root@pam!cursor_mycocomp"
TOKEN_SECRET = "74cbcb9b-53cd-4750-b77e-7b5fc395201c"
BASE_URL = "https://192.168.0.202:8006/api2/json"

session = requests.Session()
session.verify = False
session.headers["Authorization"] = f"PVEAPIToken={TOKEN_ID}={TOKEN_SECRET}"

print("Testing Proxmox API endpoints...")
print()

# Get nodes
r = session.get(f"{BASE_URL}/nodes", timeout=10)
print("NODES:", r.status_code)
nodes = r.json().get("data", [])
for n in nodes:
    node_name = n.get("node")
    print(f"  Node: {node_name}")
node_name = nodes[0].get("node") if nodes else "pve"
print(f"  Using node: {node_name}")
print()

# Get node storage with full response
r = session.get(f"{BASE_URL}/nodes/{node_name}/storage", timeout=10)
print("NODE STORAGE:", r.status_code)
storage_data = r.json()
if storage_data.get("data"):
    for s in storage_data["data"]:
        name = s.get("storage")
        stype = s.get("type", "?")
        total = s.get("total", 0) / 1024 / 1024 / 1024
        used = s.get("used", 0) / 1024 / 1024 / 1024
        content = s.get("content", "")
        active = s.get("active", 0)
        print(f"  - {name}: type={stype}, {used:.1f}/{total:.1f}GB, content={content}, active={active}")
else:
    print("  No storage found")
    print(f"  Raw response: {json.dumps(storage_data, indent=2)[:300]}")
print()

# Get cluster storage
r = session.get(f"{BASE_URL}/storage", timeout=10)
print("CLUSTER STORAGE:", r.status_code)
cluster_storage = r.json()
if cluster_storage.get("data"):
    for s in cluster_storage["data"]:
        name = s.get("storage")
        stype = s.get("type", "?")
        content = s.get("content", "")
        print(f"  - {name}: type={stype}, content={content}")
else:
    print("  No cluster storage found")
    print(f"  Raw response: {json.dumps(cluster_storage, indent=2)[:300]}")
print()

# Get node status
r = session.get(f"{BASE_URL}/nodes/{node_name}/status", timeout=10)
print("NODE STATUS:", r.status_code)
if r.status_code == 403:
    print("  ERROR: 403 Forbidden - Token lacks privileges")
    print("  The token needs 'Sys.Audit' permission on /nodes/{node}")
    status = {}
else:
    status = r.json().get("data", {}) or {}
cpuinfo = status.get("cpuinfo", {}) if status else {}
memory = status.get("memory", {}) if status else {}
rootfs = status.get("rootfs", {}) if status else {}
print(f"  CPU: {cpuinfo.get('cpus', '?')} cores, {cpuinfo.get('model', '?')}")
print(f"  Memory: {memory.get('used', 0) / 1024 / 1024 / 1024:.1f} / {memory.get('total', 0) / 1024 / 1024 / 1024:.1f} GB")
print(f"  Root FS: {rootfs.get('used', 0) / 1024 / 1024 / 1024:.1f} / {rootfs.get('total', 0) / 1024 / 1024 / 1024:.1f} GB")
print()

# Get existing VMs
r = session.get(f"{BASE_URL}/nodes/{node_name}/qemu", timeout=10)
print("VMS:", r.status_code)
vms = r.json().get("data", [])
if vms:
    for vm in vms:
        vmid = vm.get("vmid")
        name = vm.get("name", "unnamed")
        status = vm.get("status")
        print(f"  VM {vmid}: {name} ({status})")
else:
    print("  No VMs found")
print()

# Check if VM 103 exists
r = session.get(f"{BASE_URL}/nodes/{node_name}/qemu/103/status/current", timeout=10)
print("VM 103 CHECK:", r.status_code)
if r.status_code == 200:
    print("  VM 103 exists!")
    vm_status = r.json().get("data", {})
    print(f"  Status: {vm_status.get('status')}")
else:
    print("  VM 103 does not exist - ready to create!")
print()

# Check ISO storage content
print("CHECKING ISO CONTENT:")
for storage_name in ["local", "local-lvm"]:
    r = session.get(f"{BASE_URL}/nodes/{node_name}/storage/{storage_name}/content", timeout=10)
    if r.status_code == 200:
        content = r.json().get("data", [])
        isos = [c for c in content if c.get("content") == "iso"]
        if isos:
            print(f"  {storage_name}:")
            for iso in isos:
                volid = iso.get("volid", "")
                size_mb = iso.get("size", 0) / 1024 / 1024
                print(f"    - {volid} ({size_mb:.0f} MB)")
        else:
            print(f"  {storage_name}: no ISOs")
    else:
        print(f"  {storage_name}: error {r.status_code}")
print()

print("=" * 60)
print("API TEST COMPLETE")
print("=" * 60)
