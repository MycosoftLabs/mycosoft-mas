#!/usr/bin/env python3
"""Check all potential Dell servers for Proxmox."""

import socket
import requests
import urllib3
urllib3.disable_warnings()

# Dell server IPs found in scan
servers = [
    "192.168.0.90",   # Known Proxmox (MAC: 24:6E:96:60:65:CC)
    "192.168.0.120",  # Dell server (MAC: 84:2B:2B:46:13:EE)
    "192.168.0.68",   # Linux server (MAC: 8C:30:66:7A:3F:70)
]

print("=" * 70)
print("  CHECKING ALL POTENTIAL SERVERS")
print("=" * 70)

for ip in servers:
    print(f"\n{ip}:")
    
    # Check ports
    ports = [22, 80, 443, 3000, 5678, 8000, 8006, 8443]
    open_ports = []
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            if sock.connect_ex((ip, port)) == 0:
                open_ports.append(port)
            sock.close()
        except:
            pass
    
    print(f"  Open ports: {open_ports}")
    
    # Check if Proxmox
    if 8006 in open_ports:
        print("  => Proxmox detected!")
        try:
            r = requests.get(f"https://{ip}:8006/", verify=False, timeout=5)
            print(f"  Web UI: {r.status_code}")
            
            # Try auth
            r2 = requests.post(
                f"https://{ip}:8006/api2/json/access/ticket",
                data={"username": "root@pam", "password": "20202020"},
                verify=False, timeout=5
            )
            print(f"  Auth (20202020): {r2.status_code}")
            
            if r2.status_code == 200:
                print("  => AUTH SUCCESS!")
                data = r2.json()["data"]
                cookies = {"PVEAuthCookie": data["ticket"]}
                headers = {"CSRFPreventionToken": data["CSRFPreventionToken"]}
                
                # Get nodes
                r3 = requests.get(
                    f"https://{ip}:8006/api2/json/nodes",
                    cookies=cookies, headers=headers, verify=False
                )
                for node in r3.json().get("data", []):
                    node_name = node.get("node")
                    print(f"\n  Node: {node_name}")
                    
                    # Get VMs
                    r4 = requests.get(
                        f"https://{ip}:8006/api2/json/nodes/{node_name}/qemu",
                        cookies=cookies, headers=headers, verify=False
                    )
                    for vm in r4.json().get("data", []):
                        print(f"    VM {vm.get('vmid')}: {vm.get('name')} - {vm.get('status')}")
        except Exception as e:
            print(f"  Error: {e}")
    
    # Check if web server
    if 80 in open_ports or 443 in open_ports:
        for port in [443, 80]:
            if port in open_ports:
                try:
                    protocol = "https" if port == 443 else "http"
                    r = requests.get(f"{protocol}://{ip}/", verify=False, timeout=3)
                    print(f"  HTTP ({port}): {r.status_code} - {r.text[:100] if r.text else 'Empty'}...")
                except Exception as e:
                    print(f"  HTTP ({port}): Error - {e}")
    
    # Check if SSH is open
    if 22 in open_ports:
        print("  SSH: Open")

print("\n" + "=" * 70)
