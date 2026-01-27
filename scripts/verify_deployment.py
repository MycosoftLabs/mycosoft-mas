#!/usr/bin/env python3
"""Verify deployment status - January 27, 2026"""
import requests
from datetime import datetime

def check(name, url, timeout=10, expected_codes=[200]):
    try:
        r = requests.get(url, timeout=timeout)
        status = "OK" if r.status_code in expected_codes else "WARN"
        return status, r.status_code
    except requests.exceptions.ConnectionError:
        return "DOWN", "Connection refused"
    except requests.exceptions.Timeout:
        return "TIMEOUT", "Timeout"
    except Exception as e:
        return "ERROR", str(e)[:50]

def check_webhook(url, timeout=10):
    try:
        r = requests.post(url, json={"message": "test", "action": "health"}, timeout=timeout)
        return r.status_code
    except Exception as e:
        return str(e)[:30]

print("=" * 70)
print(f"DEPLOYMENT VERIFICATION - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

print("\n[n8n Services]")
status, code = check("Sandbox n8n", "http://192.168.0.187:5678/healthz", timeout=5)
print(f"  Sandbox VM (187) n8n: {status} ({code})" + (" <- Should be STOPPED" if status == "OK" else " <- CORRECT"))

status, code = check("MAS n8n", "http://192.168.0.188:5678/healthz")
print(f"  MAS VM (188) n8n:     {status} ({code})" + (" <- CORRECT" if status == "OK" else " <- SHOULD BE RUNNING"))

print("\n[External Endpoints]")
status, code = check("sandbox.mycosoft.com", "https://sandbox.mycosoft.com/api/health", timeout=15)
print(f"  sandbox.mycosoft.com: {status} ({code})")

status, code = check("dev.mycosoft.com", "https://dev.mycosoft.com/api/health", timeout=15)
print(f"  dev.mycosoft.com:     {status} ({code})")

print("\n[n8n Webhooks on MAS VM]")
webhooks = [
    ("myca/command", "http://192.168.0.188:5678/webhook/myca/command"),
    ("myca-chat", "http://192.168.0.188:5678/webhook/myca-chat"),
]
for name, url in webhooks:
    code = check_webhook(url)
    status = "OK" if isinstance(code, int) and code < 500 else ("ERR" if isinstance(code, int) else code)
    print(f"  /webhook/{name}: {code}")

print("\n[MAS API]")
status, code = check("MAS API", "http://192.168.0.188:8001/health")
print(f"  MAS API (8001): {status} ({code})")

print("\n[Summary]")
print("  - MAS n8n should be RUNNING on 192.168.0.188")
print("  - Sandbox n8n should be STOPPED on 192.168.0.187")
print("  - sandbox.mycosoft.com points to VM 103 (Sandbox)")
print("  - dev.mycosoft.com points to VM 101 (MAS)")
print()
