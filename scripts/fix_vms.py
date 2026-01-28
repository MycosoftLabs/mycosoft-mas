#!/usr/bin/env python3
"""
Fix VMs - Check Proxmox and start VMs if needed.
Also try to SSH to known VM IPs.
"""

import requests
import urllib3
import socket
import subprocess
urllib3.disable_warnings()

PROXMOX_HOST = '192.168.0.90'

# Try multiple credential combinations
CREDENTIALS = [
    ('root@pam', '20202020'),
    ('root', '20202020'),
    ('admin@pam', '20202020'),
    ('root@pam', 'Mushroom1!Mushroom1!'),
]

def try_proxmox_auth():
    """Try to authenticate to Proxmox with various credentials."""
    print("=" * 60)
    print("  PROXMOX AUTHENTICATION ATTEMPTS")
    print("=" * 60)
    
    for user, password in CREDENTIALS:
        print(f"\nTrying: {user} / {'*' * len(password)}")
        try:
            r = requests.post(
                f"https://{PROXMOX_HOST}:8006/api2/json/access/ticket",
                data={"username": user, "password": password},
                verify=False, timeout=10
            )
            print(f"  Status: {r.status_code}")
            if r.status_code == 200:
                print(f"  => SUCCESS with {user}!")
                data = r.json()["data"]
                return data["ticket"], data["CSRFPreventionToken"], user
            else:
                print(f"  Failed: {r.text[:50]}")
        except Exception as e:
            print(f"  Error: {e}")
    
    return None, None, None

def list_and_start_vms(ticket, csrf):
    """List VMs and start any that are stopped."""
    cookies = {"PVEAuthCookie": ticket}
    headers = {"CSRFPreventionToken": csrf}
    
    print("\n" + "=" * 60)
    print("  PROXMOX VMs")
    print("=" * 60)
    
    # Get nodes
    r = requests.get(
        f"https://{PROXMOX_HOST}:8006/api2/json/nodes",
        cookies=cookies, headers=headers, verify=False
    )
    
    for node in r.json().get("data", []):
        node_name = node.get("node")
        print(f"\nNode: {node_name} - Status: {node.get('status')}")
        
        # Get VMs
        r2 = requests.get(
            f"https://{PROXMOX_HOST}:8006/api2/json/nodes/{node_name}/qemu",
            cookies=cookies, headers=headers, verify=False
        )
        
        for vm in r2.json().get("data", []):
            vmid = vm.get("vmid")
            name = vm.get("name", "unknown")
            status = vm.get("status")
            print(f"  VM {vmid}: {name} - {status}")
            
            # If VM is stopped, offer to start it
            if status == "stopped":
                print(f"    -> VM is STOPPED. Starting...")
                try:
                    r3 = requests.post(
                        f"https://{PROXMOX_HOST}:8006/api2/json/nodes/{node_name}/qemu/{vmid}/status/start",
                        cookies=cookies, headers=headers, verify=False
                    )
                    if r3.status_code == 200:
                        print(f"    => Started successfully!")
                    else:
                        print(f"    => Failed to start: {r3.text[:100]}")
                except Exception as e:
                    print(f"    => Error starting: {e}")
            elif status == "running":
                # Try to get IP
                try:
                    r4 = requests.get(
                        f"https://{PROXMOX_HOST}:8006/api2/json/nodes/{node_name}/qemu/{vmid}/agent/network-get-interfaces",
                        cookies=cookies, headers=headers, verify=False, timeout=5
                    )
                    if r4.status_code == 200:
                        ifaces = r4.json().get("data", {}).get("result", [])
                        for iface in ifaces:
                            for addr in iface.get("ip-addresses", []):
                                if addr.get("ip-address-type") == "ipv4" and not addr.get("ip-address", "").startswith("127."):
                                    print(f"    -> IP: {addr.get('ip-address')}")
                except:
                    pass

def check_vm_ssh():
    """Try to connect to known VM IPs via SSH."""
    print("\n" + "=" * 60)
    print("  SSH CONNECTIVITY CHECK")
    print("=" * 60)
    
    vm_ips = [
        ("192.168.0.187", "Sandbox VM (old)"),
        ("192.168.0.188", "ubuntu-server / MAS VM"),
        ("192.168.0.163", "Unknown"),
        ("192.168.0.85", "Unknown"),
    ]
    
    for ip, desc in vm_ips:
        print(f"\n{ip} ({desc}):")
        # Check if port 22 is open
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((ip, 22))
            sock.close()
            if result == 0:
                print(f"  Port 22: OPEN")
                # Check for port 3000 (website)
                sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock2.settimeout(1)
                result2 = sock2.connect_ex((ip, 3000))
                sock2.close()
                if result2 == 0:
                    print(f"  Port 3000: OPEN (Website)")
                # Check for port 5678 (n8n)
                sock3 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock3.settimeout(1)
                result3 = sock3.connect_ex((ip, 5678))
                sock3.close()
                if result3 == 0:
                    print(f"  Port 5678: OPEN (n8n)")
            else:
                print(f"  Port 22: CLOSED or unreachable")
        except socket.timeout:
            print(f"  Timeout - host may be down")
        except Exception as e:
            print(f"  Error: {e}")

def main():
    # Try Proxmox auth
    ticket, csrf, user = try_proxmox_auth()
    
    if ticket:
        list_and_start_vms(ticket, csrf)
    else:
        print("\n[!] Could not authenticate to Proxmox")
        print("    Please check credentials or access Proxmox web UI directly:")
        print(f"    https://{PROXMOX_HOST}:8006")
    
    # Check SSH connectivity
    check_vm_ssh()
    
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"Proxmox: https://{PROXMOX_HOST}:8006")
    print("If VMs are not showing, they may need to be started from Proxmox UI")
    print("=" * 60)

if __name__ == "__main__":
    main()
