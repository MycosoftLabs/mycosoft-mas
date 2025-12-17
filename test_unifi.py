#!/usr/bin/env python3
"""Quick UniFi API test"""
import requests
import urllib3
urllib3.disable_warnings()

API_KEY = "BfRgo4k9aS0-yo8BKqXpEtdo4k2jzM8k"
HOST = "192.168.0.1"

session = requests.Session()
session.verify = False
session.headers["X-API-Key"] = API_KEY

print("=" * 50)
print("  MYCA UniFi Network Status")
print("=" * 50)
print()

# Get devices
try:
    r = session.get(f"https://{HOST}/proxy/network/api/s/default/stat/device", timeout=10)
    devices = r.json().get("data", [])
    print(f"Devices ({len(devices)}):")
    for d in devices:
        status = "online" if d.get("state") == 1 else "offline"
        print(f"  [{status}] {d.get('name', 'unnamed')} - {d.get('model', 'unknown')}")
except Exception as e:
    print(f"  Error: {e}")

# Get clients
try:
    r = session.get(f"https://{HOST}/proxy/network/api/s/default/stat/sta", timeout=10)
    clients = r.json().get("data", [])
    print(f"\nClients ({len(clients)} connected):")
    for c in clients[:10]:  # Show first 10
        name = c.get("hostname") or c.get("name") or c.get("mac", "unknown")
        ip = c.get("ip", "no IP")
        print(f"  - {name}: {ip}")
    if len(clients) > 10:
        print(f"  ... and {len(clients) - 10} more")
except Exception as e:
    print(f"  Error: {e}")

print()
print("=" * 50)
print("  MYCA has UniFi access!")
print("=" * 50)
