#!/usr/bin/env python3
"""Quick test of voice services."""
import requests

services = {
    "Moshi (8998)": "http://localhost:8998/health",
    "Bridge (8999)": "http://localhost:8999/health",
    "Website (3010)": "http://localhost:3010/",
    "MAS Consciousness": "http://192.168.0.188:8001/api/myca/status",
}

print("\n=== VOICE SYSTEM STATUS ===\n")
for name, url in services.items():
    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            print(f"[OK] {name}: ONLINE")
        else:
            print(f"[WARN] {name}: {r.status_code}")
    except Exception as e:
        print(f"[ERROR] {name}: {str(e)[:50]}")

print("\n=== READY TO TALK TO MYCA ===")
print("Open: http://localhost:3010/test-voice")
print("Click 'Start MYCA Voice' and begin speaking!")
