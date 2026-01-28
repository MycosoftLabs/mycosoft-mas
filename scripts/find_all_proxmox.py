#!/usr/bin/env python3
"""Find all Proxmox instances and check their status."""

import socket
import requests
import urllib3
import concurrent.futures
urllib3.disable_warnings()

# All potentially online IPs from scan
ONLINE_IPS = [
    "192.168.0.90",   # Confirmed Proxmox
    "192.168.0.120",  # Dell server
    "192.168.0.68",   # Linux server
]

# Known credentials
PROXMOX_CREDS = [
    ("root@pam", "20202020"),
    ("root", "20202020"),
]

print("=" * 70)
print("  PROXMOX SERVER DISCOVERY")
print("=" * 70)

def check_proxmox(ip):
    """Check if IP has Proxmox running."""
    result = {"ip": ip, "has_8006": False, "is_proxmox": False, "auth_works": False, "nodes": [], "vms": []}
    
    # Check port 8006
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        if sock.connect_ex((ip, 8006)) == 0:
            result["has_8006"] = True
        sock.close()
    except:
        pass
    
    if not result["has_8006"]:
        return result
    
    # Check if Proxmox web UI
    try:
        r = requests.get(f"https://{ip}:8006/", verify=False, timeout=5)
        if "PVE" in r.text or "Proxmox" in r.text:
            result["is_proxmox"] = True
    except:
        pass
    
    if not result["is_proxmox"]:
        return result
    
    # Try authentication
    for username, password in PROXMOX_CREDS:
        try:
            r = requests.post(
                f"https://{ip}:8006/api2/json/access/ticket",
                data={"username": username, "password": password},
                verify=False, timeout=10
            )
            if r.status_code == 200:
                result["auth_works"] = True
                result["auth_user"] = username
                
                data = r.json()["data"]
                cookies = {"PVEAuthCookie": data["ticket"]}
                headers = {"CSRFPreventionToken": data["CSRFPreventionToken"]}
                
                # Get nodes
                r2 = requests.get(
                    f"https://{ip}:8006/api2/json/nodes",
                    cookies=cookies, headers=headers, verify=False
                )
                for node in r2.json().get("data", []):
                    node_name = node.get("node")
                    result["nodes"].append(node_name)
                    
                    # Get VMs
                    r3 = requests.get(
                        f"https://{ip}:8006/api2/json/nodes/{node_name}/qemu",
                        cookies=cookies, headers=headers, verify=False
                    )
                    for vm in r3.json().get("data", []):
                        vm_info = {
                            "vmid": vm.get("vmid"),
                            "name": vm.get("name"),
                            "status": vm.get("status"),
                        }
                        
                        # Get IP if running
                        if vm.get("status") == "running":
                            try:
                                r4 = requests.get(
                                    f"https://{ip}:8006/api2/json/nodes/{node_name}/qemu/{vm.get('vmid')}/agent/network-get-interfaces",
                                    cookies=cookies, headers=headers, verify=False, timeout=5
                                )
                                if r4.status_code == 200:
                                    for iface in r4.json().get("data", {}).get("result", []):
                                        for addr in iface.get("ip-addresses", []):
                                            if addr.get("ip-address-type") == "ipv4" and not addr.get("ip-address", "").startswith("127."):
                                                vm_info["ip"] = addr.get("ip-address")
                            except:
                                pass
                        
                        result["vms"].append(vm_info)
                break
        except:
            pass
    
    return result

# Check all IPs in parallel
print("\nScanning for Proxmox instances...")
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(check_proxmox, ONLINE_IPS))

# Display results
for result in results:
    ip = result["ip"]
    print(f"\n{ip}:")
    print(f"  Port 8006: {'OPEN' if result['has_8006'] else 'CLOSED'}")
    
    if result["has_8006"]:
        print(f"  Proxmox: {'YES' if result['is_proxmox'] else 'NO'}")
        
        if result["is_proxmox"]:
            print(f"  Auth: {'SUCCESS (' + result.get('auth_user', '') + ')' if result['auth_works'] else 'FAILED'}")
            
            if result["auth_works"]:
                print(f"  Nodes: {result['nodes']}")
                print(f"  VMs:")
                for vm in result["vms"]:
                    ip_str = f" - IP: {vm.get('ip', 'N/A')}" if vm.get('ip') else ""
                    print(f"    VM {vm['vmid']}: {vm['name']} - {vm['status']}{ip_str}")

# Also scan for SSH access on servers
print("\n" + "=" * 70)
print("  SSH ACCESS CHECK")
print("=" * 70)

for ip in ONLINE_IPS:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        if sock.connect_ex((ip, 22)) == 0:
            print(f"\n{ip}: SSH OPEN")
        sock.close()
    except:
        pass

print("\n" + "=" * 70)
