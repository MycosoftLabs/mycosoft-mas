#!/usr/bin/env python3
"""Test MycoBrain connectivity end-to-end for sandbox.mycosoft.com.

This script checks:
- sandbox -> /api/mycobrain/* (Cloudflare tunnel -> Windows LAN MycoBrain service)
- sandbox -> /natureos/devices (Website UI reachability sanity)

It does NOT assume a local website is running.
"""

import requests
import sys

print("=" * 80)
print("MYCOBRAIN CONNECTIVITY TEST")
print("=" * 80)

# Test localhost:3000
print("\n1. TESTING SANDBOX.MYCOSOFT.COM")
print("-" * 80)

sandbox_endpoints = [
    "/api/mycobrain/health",
    "/api/mycobrain/ports",
    "/api/mycobrain/devices",
    "/natureos/devices",
]

results = []
for endpoint in sandbox_endpoints:
    try:
        url = f"https://sandbox.mycosoft.com{endpoint}"
        response = requests.get(url, timeout=10, verify=True)
        status = "OK" if response.status_code == 200 else f"HTTP {response.status_code}"
        print(f"  {endpoint:40s} {status}")
        results.append((endpoint, response.status_code))
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"    Response keys: {list(data.keys())[:5] if isinstance(data, dict) else 'N/A'}")
            except:
                pass
    except requests.exceptions.ConnectionError:
        print(f"  {endpoint:40s} CONNECTION REFUSED")
        results.append((endpoint, 0))
    except requests.exceptions.SSLError as e:
        print(f"  {endpoint:40s} SSL ERROR: {str(e)[:50]}")
        results.append((endpoint, 0))
    except Exception as e:
        print(f"  {endpoint:40s} ERROR: {str(e)[:50]}")
        results.append((endpoint, 0))

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

mycobrain_ok = all(code == 200 for ep, code in results if ep.startswith("/api/mycobrain/"))
website_ok = next((code for ep, code in results if ep == "/natureos/devices"), 0) == 200

print(f"MycoBrain API (sandbox /api/mycobrain/*): {'OK' if mycobrain_ok else 'NOT OK'}")
print(f"Website UI reachability (/natureos/devices): {'OK' if website_ok else 'NOT OK'}")

if not mycobrain_ok:
    print("\nIf MycoBrain API is NOT OK, likely causes:")
    print("- Windows MycoBrain service not running on 192.168.0.172:8003")
    print("- Windows firewall blocking inbound 8003")
    print("- VM cloudflared connector not active (split-brain connector issue)")
    print("\nFix path:")
    print("- Start Windows service: scripts/start_mycobrain_minimal_service.ps1 (or your website repo MycoBrain service)")
    print("- Verify VM ingress order: python scripts/inspect_cloudflared_config.py")
    print("- Verify VM -> Windows reachability: python scripts/check_mycobrain_vm.py")
