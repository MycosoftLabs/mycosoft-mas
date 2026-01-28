#!/usr/bin/env python3
"""
Full Network Discovery - After Rewiring
Discovers all devices, Proxmox instances, VMs, and network topology.
"""

import socket
import subprocess
import json
import requests
import urllib3
import concurrent.futures
from datetime import datetime
urllib3.disable_warnings()

print("=" * 70)
print("  MYCOSOFT FULL NETWORK DISCOVERY")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# Known infrastructure
KNOWN_ROLES = {
    "192.168.0.1": "Dream Machine (Gateway)",
    "192.168.0.2": "10G Switch / USW Pro Max 24 PoE",
    "192.168.0.105": "NAS (UNAS-Pro)",
    "192.168.0.172": "Windows Dev PC (MycoComp)",
    "192.168.0.187": "Sandbox VM (expected)",
    "192.168.0.188": "MAS VM (expected)",
    "192.168.0.202": "Proxmox Server #1 (old IP)",
    "192.168.0.203": "Proxmox Server #2 (old IP)",
    "192.168.0.204": "Proxmox Server #3 (old IP)",
}

# Port signatures for device identification
PORT_SIGNATURES = {
    22: "SSH",
    80: "HTTP",
    443: "HTTPS/UniFi",
    3000: "Website (Next.js)",
    3389: "RDP (Windows)",
    5000: "NAS DSM",
    5001: "NAS DSM SSL",
    5678: "n8n",
    8000: "MINDEX API",
    8003: "MycoBrain",
    8006: "Proxmox",
    8080: "HTTP Alt",
    8443: "UniFi Controller",
    9090: "Prometheus",
}

def ping_host(ip, timeout=1):
    """Quick ping check."""
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", str(timeout * 1000), ip],
            capture_output=True, text=True, timeout=timeout + 1
        )
        return "Reply from" in result.stdout and "Destination host unreachable" not in result.stdout
    except:
        return False

def scan_ports(ip, ports, timeout=0.5):
    """Scan multiple ports on an IP."""
    open_ports = []
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            if sock.connect_ex((ip, port)) == 0:
                open_ports.append(port)
            sock.close()
        except:
            pass
    return open_ports

def get_mac_from_arp(ip):
    """Get MAC address from ARP table."""
    try:
        result = subprocess.run(["arp", "-a", ip], capture_output=True, text=True, timeout=5)
        for line in result.stdout.split('\n'):
            if ip in line:
                parts = line.split()
                for part in parts:
                    if '-' in part and len(part) == 17:
                        return part.replace('-', ':').upper()
    except:
        pass
    return None

def identify_device(ip, open_ports):
    """Identify device type based on open ports."""
    if 8006 in open_ports:
        return "PROXMOX"
    if 8443 in open_ports or (443 in open_ports and 22 in open_ports):
        return "UNIFI/NETWORK"
    if 5000 in open_ports or 5001 in open_ports:
        return "NAS"
    if 3389 in open_ports:
        return "WINDOWS"
    if 3000 in open_ports:
        return "WEBSITE/VM"
    if 5678 in open_ports:
        return "N8N/MAS"
    if 8000 in open_ports:
        return "MINDEX"
    if 22 in open_ports:
        return "LINUX/SERVER"
    if 80 in open_ports or 443 in open_ports:
        return "WEB DEVICE"
    return "UNKNOWN"

def check_proxmox_api(ip):
    """Check if Proxmox API is accessible and try auth."""
    try:
        r = requests.get(f"https://{ip}:8006/", verify=False, timeout=3)
        if r.status_code == 200 and ("PVE" in r.text or "Proxmox" in r.text):
            # Try authentication
            for password in ["20202020", "Mushroom1!Mushroom1!", ""]:
                try:
                    r2 = requests.post(
                        f"https://{ip}:8006/api2/json/access/ticket",
                        data={"username": "root@pam", "password": password},
                        verify=False, timeout=5
                    )
                    if r2.status_code == 200:
                        return {"accessible": True, "auth": True, "password": password[:3] + "***"}
                except:
                    pass
            return {"accessible": True, "auth": False}
    except:
        pass
    return {"accessible": False, "auth": False}

def check_unifi_api(ip):
    """Check UniFi controller API."""
    try:
        # Try the default UniFi API endpoint
        r = requests.get(f"https://{ip}/api/self", verify=False, timeout=3)
        return r.status_code in [200, 401]
    except:
        return False

# ============================================================
# STEP 1: Full Subnet Scan
# ============================================================
print("\n" + "=" * 70)
print("  STEP 1: SUBNET SCAN (192.168.0.0/24)")
print("=" * 70)

ports_to_scan = list(PORT_SIGNATURES.keys())
discovered_devices = []

def scan_ip(i):
    ip = f"192.168.0.{i}"
    if ping_host(ip, timeout=0.5):
        open_ports = scan_ports(ip, ports_to_scan, timeout=0.3)
        mac = get_mac_from_arp(ip)
        device_type = identify_device(ip, open_ports)
        known_role = KNOWN_ROLES.get(ip, "")
        return {
            "ip": ip,
            "mac": mac,
            "open_ports": open_ports,
            "device_type": device_type,
            "known_role": known_role,
        }
    return None

print("Scanning 192.168.0.1-254...")
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
    futures = {executor.submit(scan_ip, i): i for i in range(1, 255)}
    for future in concurrent.futures.as_completed(futures):
        result = future.result()
        if result:
            discovered_devices.append(result)

# Sort by IP
discovered_devices.sort(key=lambda x: [int(p) for p in x["ip"].split(".")])

print(f"\nDiscovered {len(discovered_devices)} devices:\n")
print(f"{'IP':<16} {'MAC':<20} {'TYPE':<15} {'PORTS':<30} {'ROLE'}")
print("-" * 100)
for dev in discovered_devices:
    ports_str = ",".join(str(p) for p in dev["open_ports"][:6])
    if len(dev["open_ports"]) > 6:
        ports_str += "..."
    print(f"{dev['ip']:<16} {dev['mac'] or 'N/A':<20} {dev['device_type']:<15} {ports_str:<30} {dev['known_role']}")

# ============================================================
# STEP 2: Identify Proxmox Servers
# ============================================================
print("\n" + "=" * 70)
print("  STEP 2: PROXMOX SERVERS")
print("=" * 70)

proxmox_servers = [dev for dev in discovered_devices if dev["device_type"] == "PROXMOX" or 8006 in dev.get("open_ports", [])]

if proxmox_servers:
    for pve in proxmox_servers:
        print(f"\n{pve['ip']}:")
        print(f"  MAC: {pve['mac']}")
        print(f"  Ports: {pve['open_ports']}")
        
        # Check API
        api_status = check_proxmox_api(pve['ip'])
        print(f"  Web UI: {'Accessible' if api_status['accessible'] else 'Not accessible'}")
        print(f"  API Auth: {'SUCCESS (' + api_status.get('password', '') + ')' if api_status['auth'] else 'FAILED'}")
        
        if api_status['auth']:
            # Get VM list
            try:
                password = "20202020" if api_status.get('password', '').startswith('202') else ""
                r = requests.post(
                    f"https://{pve['ip']}:8006/api2/json/access/ticket",
                    data={"username": "root@pam", "password": password},
                    verify=False, timeout=5
                )
                if r.status_code == 200:
                    data = r.json()["data"]
                    cookies = {"PVEAuthCookie": data["ticket"]}
                    headers = {"CSRFPreventionToken": data["CSRFPreventionToken"]}
                    
                    # Get nodes
                    r2 = requests.get(
                        f"https://{pve['ip']}:8006/api2/json/nodes",
                        cookies=cookies, headers=headers, verify=False
                    )
                    for node in r2.json().get("data", []):
                        node_name = node.get("node")
                        print(f"\n  Node: {node_name}")
                        
                        # Get VMs
                        r3 = requests.get(
                            f"https://{pve['ip']}:8006/api2/json/nodes/{node_name}/qemu",
                            cookies=cookies, headers=headers, verify=False
                        )
                        for vm in r3.json().get("data", []):
                            vmid = vm.get("vmid")
                            name = vm.get("name", "unknown")
                            status = vm.get("status")
                            print(f"    VM {vmid}: {name} - {status}")
                            
                            # Get IP if running
                            if status == "running":
                                try:
                                    r4 = requests.get(
                                        f"https://{pve['ip']}:8006/api2/json/nodes/{node_name}/qemu/{vmid}/agent/network-get-interfaces",
                                        cookies=cookies, headers=headers, verify=False, timeout=5
                                    )
                                    if r4.status_code == 200:
                                        for iface in r4.json().get("data", {}).get("result", []):
                                            for addr in iface.get("ip-addresses", []):
                                                if addr.get("ip-address-type") == "ipv4" and not addr.get("ip-address", "").startswith("127."):
                                                    print(f"      -> IP: {addr.get('ip-address')}")
                                except:
                                    pass
            except Exception as e:
                print(f"  Error getting VMs: {e}")
else:
    print("\nNo Proxmox servers found with port 8006 open.")
    print("Checking additional IPs that might be Proxmox...")
    
    # Check old known Proxmox IPs
    for ip in ["192.168.0.90", "192.168.0.202", "192.168.0.203", "192.168.0.204"]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            if sock.connect_ex((ip, 8006)) == 0:
                print(f"  {ip}:8006 - OPEN (Proxmox)")
                api_status = check_proxmox_api(ip)
                print(f"    Auth: {'SUCCESS' if api_status['auth'] else 'FAILED'}")
            sock.close()
        except:
            pass

# ============================================================
# STEP 3: Identify VMs (SSH check on likely IPs)
# ============================================================
print("\n" + "=" * 70)
print("  STEP 3: VM IDENTIFICATION")
print("=" * 70)

vm_candidates = [dev for dev in discovered_devices if dev["device_type"] in ["LINUX/SERVER", "WEBSITE/VM", "N8N/MAS", "MINDEX"]]

if vm_candidates:
    print("\nPotential VMs found:")
    for vm in vm_candidates:
        print(f"\n{vm['ip']}:")
        print(f"  Type: {vm['device_type']}")
        print(f"  MAC: {vm['mac']}")
        print(f"  Ports: {vm['open_ports']}")
        
        # Check for services
        if 3000 in vm['open_ports']:
            print("  -> Website container likely running")
        if 5678 in vm['open_ports']:
            print("  -> n8n likely running")
        if 8000 in vm['open_ports']:
            print("  -> MINDEX API likely running")
else:
    print("\nNo VMs detected. They may be stopped.")

# ============================================================
# STEP 4: UniFi Network Devices
# ============================================================
print("\n" + "=" * 70)
print("  STEP 4: UNIFI NETWORK DEVICES")
print("=" * 70)

unifi_devices = [dev for dev in discovered_devices if dev["device_type"] == "UNIFI/NETWORK" or 8443 in dev.get("open_ports", [])]

print(f"\nFound {len(unifi_devices)} UniFi/Network devices:")
for dev in unifi_devices:
    print(f"  {dev['ip']} - {dev['mac']} - Ports: {dev['open_ports']}")

# ============================================================
# STEP 5: Network Topology Summary
# ============================================================
print("\n" + "=" * 70)
print("  STEP 5: NETWORK TOPOLOGY SUMMARY")
print("=" * 70)

# Categorize devices
categories = {
    "Gateway/Router": [],
    "Switches": [],
    "Proxmox Servers": [],
    "VMs": [],
    "NAS": [],
    "Workstations": [],
    "Network Devices": [],
    "Unknown": [],
}

for dev in discovered_devices:
    ip = dev["ip"]
    dtype = dev["device_type"]
    
    if ip == "192.168.0.1":
        categories["Gateway/Router"].append(dev)
    elif dtype == "PROXMOX":
        categories["Proxmox Servers"].append(dev)
    elif dtype == "NAS":
        categories["NAS"].append(dev)
    elif dtype == "WINDOWS":
        categories["Workstations"].append(dev)
    elif dtype in ["WEBSITE/VM", "N8N/MAS", "MINDEX", "LINUX/SERVER"]:
        categories["VMs"].append(dev)
    elif dtype == "UNIFI/NETWORK":
        categories["Network Devices"].append(dev)
    elif 8443 in dev.get("open_ports", []) or ip == "192.168.0.2":
        categories["Switches"].append(dev)
    else:
        categories["Unknown"].append(dev)

for category, devices in categories.items():
    if devices:
        print(f"\n{category}:")
        for dev in devices:
            print(f"  {dev['ip']:<16} {dev['mac'] or 'N/A':<20} {dev['known_role'] or dev['device_type']}")

# ============================================================
# STEP 6: Save Results
# ============================================================
print("\n" + "=" * 70)
print("  SAVING RESULTS")
print("=" * 70)

results = {
    "scan_time": datetime.now().isoformat(),
    "total_devices": len(discovered_devices),
    "devices": discovered_devices,
    "proxmox_servers": proxmox_servers,
    "vm_candidates": vm_candidates,
    "unifi_devices": unifi_devices,
}

with open("docs/NETWORK_DISCOVERY_RESULTS.json", "w") as f:
    json.dump(results, f, indent=2)
print("Results saved to docs/NETWORK_DISCOVERY_RESULTS.json")

print("\n" + "=" * 70)
print("  DISCOVERY COMPLETE")
print("=" * 70)
