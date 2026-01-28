#!/usr/bin/env python3
"""Find Proxmox server on network."""

import socket
import requests
import urllib3
urllib3.disable_warnings()

# IPs from network scan
ips_to_check = [
    "192.168.0.1",
    "192.168.0.2", 
    "192.168.0.34",
    "192.168.0.68",
    "192.168.0.85",
    "192.168.0.90",
    "192.168.0.105",
    "192.168.0.120",
    "192.168.0.163",
    "192.168.0.172",
    "192.168.0.183",
]

print("=" * 60)
print("  FINDING PROXMOX SERVER (port 8006)")
print("=" * 60)

for ip in ips_to_check:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((ip, 8006))
        sock.close()
        if result == 0:
            print(f"\n[FOUND] {ip}:8006 is OPEN")
            # Try to access Proxmox API
            try:
                r = requests.get(f"https://{ip}:8006/", verify=False, timeout=5)
                print(f"  HTTP Status: {r.status_code}")
                if "PVE" in r.text or "Proxmox" in r.text:
                    print(f"  => CONFIRMED: This is Proxmox!")
                    
                    # Try authentication
                    r2 = requests.post(
                        f"https://{ip}:8006/api2/json/access/ticket",
                        data={"username": "root@pam", "password": "20202020"},
                        verify=False, timeout=10
                    )
                    print(f"  Auth Status: {r2.status_code}")
                    if r2.status_code == 200:
                        print(f"  => AUTH SUCCESS!")
                        data = r2.json()["data"]
                        ticket = data["ticket"]
                        csrf = data["CSRFPreventionToken"]
                        
                        # Get nodes
                        cookies = {"PVEAuthCookie": ticket}
                        headers = {"CSRFPreventionToken": csrf}
                        r3 = requests.get(
                            f"https://{ip}:8006/api2/json/nodes",
                            cookies=cookies, headers=headers, verify=False
                        )
                        for node in r3.json().get("data", []):
                            print(f"  Node: {node.get('node')} - Status: {node.get('status')}")
                            
                            # Get VMs
                            node_name = node.get("node")
                            r4 = requests.get(
                                f"https://{ip}:8006/api2/json/nodes/{node_name}/qemu",
                                cookies=cookies, headers=headers, verify=False
                            )
                            for vm in r4.json().get("data", []):
                                print(f"    VM {vm.get('vmid')}: {vm.get('name')} - {vm.get('status')}")
                    else:
                        print(f"  Auth failed: {r2.text[:100]}")
            except Exception as e:
                print(f"  Error accessing: {e}")
    except socket.timeout:
        pass
    except Exception as e:
        pass

print("\n" + "=" * 60)
print("  CHECKING FOR UNIFI CONTROLLER (port 443/8443)")
print("=" * 60)

for ip in ips_to_check:
    for port in [443, 8443]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((ip, port))
            sock.close()
            if result == 0:
                try:
                    r = requests.get(f"https://{ip}:{port}/", verify=False, timeout=3)
                    if "UniFi" in r.text or "ubnt" in r.text.lower():
                        print(f"\n[FOUND] {ip}:{port} - UniFi Controller!")
                except:
                    pass
        except:
            pass

print("\n" + "=" * 60)
