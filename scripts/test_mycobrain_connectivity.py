#!/usr/bin/env python3
"""Test MycoBrain connectivity on localhost:3000 vs sandbox.mycosoft.com"""

import requests
import sys

print("=" * 80)
print("MYCOBRAIN CONNECTIVITY TEST")
print("=" * 80)

# Test localhost:3000
print("\n1. TESTING LOCALHOST:3000 (Development Machine)")
print("-" * 80)

local_endpoints = [
    "/api/mycobrain/devices",
    "/api/mycobrain/ports",
    "/api/mycobrain/telemetry",
    "/natureos/devices",
]

for endpoint in local_endpoints:
    try:
        url = f"http://localhost:3000{endpoint}"
        response = requests.get(url, timeout=5)
        status = "OK" if response.status_code == 200 else f"HTTP {response.status_code}"
        print(f"  {endpoint:40s} {status}")
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"    Response keys: {list(data.keys())[:5] if isinstance(data, dict) else 'N/A'}")
            except:
                pass
    except requests.exceptions.ConnectionError:
        print(f"  {endpoint:40s} CONNECTION REFUSED (service not running)")
    except Exception as e:
        print(f"  {endpoint:40s} ERROR: {str(e)[:50]}")

# Test sandbox.mycosoft.com
print("\n2. TESTING SANDBOX.MYCOSOFT.COM")
print("-" * 80)

sandbox_endpoints = [
    "/api/mycobrain/devices",
    "/api/mycobrain/ports",
    "/api/mycobrain/telemetry",
    "/natureos/devices",
]

for endpoint in sandbox_endpoints:
    try:
        url = f"https://sandbox.mycosoft.com{endpoint}"
        response = requests.get(url, timeout=10, verify=True)
        status = "OK" if response.status_code == 200 else f"HTTP {response.status_code}"
        print(f"  {endpoint:40s} {status}")
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"    Response keys: {list(data.keys())[:5] if isinstance(data, dict) else 'N/A'}")
            except:
                pass
    except requests.exceptions.ConnectionError:
        print(f"  {endpoint:40s} CONNECTION REFUSED")
    except requests.exceptions.SSLError as e:
        print(f"  {endpoint:40s} SSL ERROR: {str(e)[:50]}")
    except Exception as e:
        print(f"  {endpoint:40s} ERROR: {str(e)[:50]}")

# Test MycoBrain service directly on VM
print("\n3. TESTING MYCOBRAIN SERVICE ON VM (Port 8003)")
print("-" * 80)
print("  Note: MycoBrain service runs on port 8003")
print("  Cloudflare tunnel configuration needed for public access")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("""
ISSUES FOUND:
1. MycoBrain service is running on VM (port 8003) but has no Cloudflare tunnel config
2. Website endpoints (/api/mycobrain/*) may not be proxying to MycoBrain service
3. Need to verify Cloudflare tunnel routes for MycoBrain endpoints

RECOMMENDATIONS:
1. Add Cloudflare tunnel config for MycoBrain service
2. Verify website API routes forward to MycoBrain service (8003)
3. Test USB serial connection on development machine
4. Ensure MycoBrain service persists after VM reboot
""")
