#!/usr/bin/env python3
"""
Test connectivity to all Mycosoft infrastructure
No credentials required - just checks network reachability
"""

import requests
import urllib3
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Infrastructure IPs - no secrets here
PROXMOX_HOSTS = [
    {"name": "Build Node", "ip": "192.168.0.202", "port": 8006},
    {"name": "DC1", "ip": "192.168.0.2", "port": 8006},
    {"name": "DC2", "ip": "192.168.0.131", "port": 8006},
]

UNIFI_HOST = {"name": "UniFi UDM", "ip": "192.168.0.1", "port": 443}


def test_proxmox(host: dict) -> bool:
    """Test Proxmox connectivity (no auth required)"""
    ip = host["ip"]
    port = host["port"]
    name = host["name"]
    
    try:
        url = f"https://{ip}:{port}/api2/json/version"
        response = requests.get(url, verify=False, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            version = data.get("data", {}).get("version", "unknown")
            print(f"  [OK] {name} ({ip}:{port}): Proxmox v{version}")
            return True
        elif response.status_code == 401:
            print(f"  [OK] {name} ({ip}:{port}): Reachable (auth required)")
            return True
        else:
            print(f"  [??] {name} ({ip}:{port}): Status {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"  [FAIL] {name} ({ip}:{port}): TIMEOUT")
        return False
    except requests.exceptions.ConnectionError:
        print(f"  [FAIL] {name} ({ip}:{port}): CONNECTION REFUSED")
        return False
    except Exception as e:
        print(f"  [FAIL] {name} ({ip}:{port}): {e}")
        return False


def test_unifi(host: dict) -> bool:
    """Test UniFi connectivity (no auth required)"""
    ip = host["ip"]
    port = host["port"]
    name = host["name"]
    
try:
        url = f"https://{ip}:{port}/"
        response = requests.get(url, verify=False, timeout=5, allow_redirects=False)
        
        if response.status_code in [200, 302, 401, 403]:
            print(f"  [OK] {name} ({ip}:{port}): Reachable")
            return True
    else:
            print(f"  [??] {name} ({ip}:{port}): Status {response.status_code}")
            return False
            
except requests.exceptions.Timeout:
        print(f"  [FAIL] {name} ({ip}:{port}): TIMEOUT")
        return False
    except requests.exceptions.ConnectionError:
        print(f"  [FAIL] {name} ({ip}:{port}): CONNECTION REFUSED")
        return False
    except Exception as e:
        print(f"  [FAIL] {name} ({ip}:{port}): {e}")
        return False


def test_vault() -> bool:
    """Test Vault connectivity"""
    try:
        url = "http://127.0.0.1:8200/v1/sys/health"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("sealed", True):
                print("  [WARN] Vault (127.0.0.1:8200): Running but SEALED")
            else:
                print("  [OK] Vault (127.0.0.1:8200): Running and unsealed")
            return True
        elif response.status_code == 503:
            print("  [WARN] Vault (127.0.0.1:8200): Running but SEALED")
            return True
        else:
            print(f"  [??] Vault (127.0.0.1:8200): Status {response.status_code}")
            return False
            
except requests.exceptions.ConnectionError:
        print("  [INFO] Vault (127.0.0.1:8200): Not running")
        return False
except Exception as e:
        print(f"  [FAIL] Vault: {e}")
        return False


def main():
    print("=" * 60)
    print("Mycosoft Infrastructure Connectivity Test")
    print("=" * 60)
    print()
    print("No credentials required - testing network reachability only.")
    print()
    
    results = {"ok": 0, "fail": 0}
    
    # Test Vault
    print("[Vault]")
    if test_vault():
        results["ok"] += 1
    else:
        # Not a failure if Vault isn't set up yet
        pass
    
    # Test Proxmox
    print()
    print("[Proxmox Hosts]")
    proxmox_reachable = 0
    for host in PROXMOX_HOSTS:
        if test_proxmox(host):
            proxmox_reachable += 1
            results["ok"] += 1
        else:
            results["fail"] += 1
    
    # Test UniFi
    print()
    print("[UniFi]")
    if test_unifi(UNIFI_HOST):
        results["ok"] += 1
    else:
        results["fail"] += 1
    
    # Summary
    print()
print("=" * 60)
    print(f"Results: {results['ok']} OK, {results['fail']} FAILED")
    
    if results["fail"] > 0:
        print()
        print("Some hosts are not reachable. Check:")
        print("  - Network connectivity")
        print("  - Firewall rules")
        print("  - Service status on target hosts")
        return 1
    
    if proxmox_reachable == 0:
        print()
        print("WARNING: No Proxmox hosts are reachable!")
        return 1
    
    print()
    print("All infrastructure is reachable.")
    print("Run bootstrap_mycosoft.sh --apply to configure API tokens.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
