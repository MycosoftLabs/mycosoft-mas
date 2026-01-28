#!/usr/bin/env python3
"""
Network Health Check - January 27, 2026
Verifies Proxmox VMs and UniFi network devices after switch installation
"""
import requests
import urllib3
import socket
import subprocess
from datetime import datetime

urllib3.disable_warnings()

# Configuration
PROXMOX_HOST = "192.168.0.202"
PROXMOX_PORT = 8006
PROXMOX_TOKEN = "root@pam!cursor_agent=bc1c9dc7-6fca-4e89-8a1d-557a9d117a3e"

UNIFI_HOST = "192.168.0.1"
UNIFI_PORT = 443

# Expected devices
EXPECTED_VMS = {
    101: {"name": "MAS VM", "ip": "192.168.0.188"},
    103: {"name": "Sandbox VM", "ip": "192.168.0.187"},
}

EXPECTED_DEVICES = [
    {"name": "Dream Machine", "ip": "192.168.0.1"},
    {"name": "Proxmox Host", "ip": "192.168.0.202"},
    {"name": "MAS VM", "ip": "192.168.0.188"},
    {"name": "Sandbox VM", "ip": "192.168.0.187"},
    {"name": "NAS", "ip": "192.168.0.2"},
]


def log(msg, status="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    symbols = {"INFO": "[i]", "OK": "[+]", "WARN": "[!]", "ERR": "[X]", "RUN": "[>]"}
    print(f"[{ts}] {symbols.get(status, '*')} {msg}")


def ping(host, timeout=2):
    """Ping a host and return True if reachable"""
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", str(timeout * 1000), host],
            capture_output=True,
            timeout=timeout + 1
        )
        return result.returncode == 0 and b"TTL=" in result.stdout
    except Exception:
        return False


def check_port(host, port, timeout=3):
    """Check if a port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def check_proxmox():
    """Check Proxmox API and VMs"""
    log("Checking Proxmox...", "RUN")
    
    if not ping(PROXMOX_HOST):
        log(f"Proxmox host {PROXMOX_HOST} is OFFLINE", "ERR")
        return False, []
    
    log(f"Proxmox host {PROXMOX_HOST} is reachable", "OK")
    
    if not check_port(PROXMOX_HOST, PROXMOX_PORT):
        log(f"Proxmox API port {PROXMOX_PORT} not responding", "ERR")
        return False, []
    
    # Check API
    headers = {"Authorization": f"PVEAPIToken={PROXMOX_TOKEN}"}
    try:
        r = requests.get(
            f"https://{PROXMOX_HOST}:{PROXMOX_PORT}/api2/json/nodes/pve/qemu",
            headers=headers,
            verify=False,
            timeout=10
        )
        if r.ok:
            vms = r.json().get("data", [])
            log(f"Proxmox API OK - {len(vms)} VMs found", "OK")
            return True, vms
        else:
            log(f"Proxmox API error: {r.status_code}", "ERR")
    except Exception as e:
        log(f"Proxmox API error: {e}", "ERR")
    
    return False, []


def check_vms(vms):
    """Check VM status and IPs"""
    log("Checking VMs...", "RUN")
    
    for vm in vms:
        vmid = vm.get("vmid")
        name = vm.get("name", "Unknown")
        status = vm.get("status", "unknown")
        
        expected = EXPECTED_VMS.get(vmid, {})
        expected_ip = expected.get("ip", "unknown")
        
        status_icon = "OK" if status == "running" else "WARN"
        log(f"VM {vmid} ({name}): {status} - Expected IP: {expected_ip}", status_icon)
        
        if status == "running" and expected_ip != "unknown":
            if ping(expected_ip):
                log(f"  {expected_ip} responds to ping", "OK")
            else:
                log(f"  {expected_ip} NOT reachable - IP may have changed!", "ERR")


def check_unifi():
    """Check UniFi controller"""
    log("Checking UniFi Controller...", "RUN")
    
    if not ping(UNIFI_HOST):
        log(f"UniFi Controller {UNIFI_HOST} is OFFLINE", "ERR")
        return False
    
    log(f"UniFi Controller {UNIFI_HOST} is reachable", "OK")
    
    if check_port(UNIFI_HOST, UNIFI_PORT):
        log(f"UniFi web interface port {UNIFI_PORT} is open", "OK")
        return True
    else:
        log(f"UniFi web interface port {UNIFI_PORT} not responding", "WARN")
        return False


def check_all_devices():
    """Ping all expected devices"""
    log("Checking all expected devices...", "RUN")
    
    online = []
    offline = []
    
    for device in EXPECTED_DEVICES:
        name = device["name"]
        ip = device["ip"]
        
        if ping(ip):
            log(f"{name} ({ip}): ONLINE", "OK")
            online.append(device)
        else:
            log(f"{name} ({ip}): OFFLINE", "ERR")
            offline.append(device)
    
    return online, offline


def find_new_devices():
    """Scan for devices that might have new IPs"""
    log("Scanning for devices (192.168.0.180-200)...", "RUN")
    
    found = []
    for i in range(180, 201):
        ip = f"192.168.0.{i}"
        if ping(ip, timeout=1):
            log(f"  Found device at {ip}", "OK")
            found.append(ip)
    
    return found


def main():
    print("=" * 60)
    print("NETWORK HEALTH CHECK")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Check all devices first
    online, offline = check_all_devices()
    
    print()
    
    # Check Proxmox
    proxmox_ok, vms = check_proxmox()
    
    if proxmox_ok:
        print()
        check_vms(vms)
    
    print()
    
    # Check UniFi
    check_unifi()
    
    # If some devices are offline, scan for new IPs
    if offline:
        print()
        log(f"{len(offline)} devices offline, scanning for new IPs...", "RUN")
        new_ips = find_new_devices()
        if new_ips:
            log(f"Found {len(new_ips)} devices in scan range", "INFO")
    
    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Online: {len(online)}/{len(EXPECTED_DEVICES)}")
    print(f"Offline: {len(offline)}")
    
    if offline:
        print()
        print("Offline devices:")
        for d in offline:
            print(f"  - {d['name']} ({d['ip']})")
    
    if proxmox_ok:
        print()
        print("Proxmox VMs:")
        for vm in vms:
            print(f"  - VM {vm.get('vmid')}: {vm.get('name')} ({vm.get('status')})")


if __name__ == "__main__":
    main()
