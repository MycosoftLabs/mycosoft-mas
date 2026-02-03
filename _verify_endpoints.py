#!/usr/bin/env python3
"""Verify new API endpoints are available."""

import requests
import time

MAS_URL = "http://192.168.0.188:8001"

print("Waiting 5 seconds for container to start...")
time.sleep(5)

print("\nTesting new API endpoints:")
print("=" * 50)

# Check health
try:
    r = requests.get(f"{MAS_URL}/health", timeout=10)
    print(f"Health: {r.status_code} - {r.json().get('status')}")
except Exception as e:
    print(f"Health: ERROR - {e}")

# Get OpenAPI spec
try:
    r = requests.get(f"{MAS_URL}/openapi.json", timeout=10)
    spec = r.json()
    paths = spec.get("paths", {})
    
    memory_paths = [p for p in paths.keys() if "memory" in p]
    security_paths = [p for p in paths.keys() if "security" in p]
    
    print("\nMemory Endpoints:")
    for p in sorted(memory_paths):
        methods = ", ".join(paths[p].keys()).upper()
        print(f"  {methods}: {p}")
    
    print("\nSecurity Endpoints:")
    for p in sorted(security_paths):
        methods = ", ".join(paths[p].keys()).upper()
        print(f"  {methods}: {p}")
        
except Exception as e:
    print(f"OpenAPI: ERROR - {e}")

# Test memory write
print("\n" + "=" * 50)
print("Testing Memory Write:")
try:
    payload = {
        "scope": "system",
        "namespace": "test:verification",
        "key": "test_key",
        "value": {"verified": True},
        "source": "system"
    }
    r = requests.post(f"{MAS_URL}/api/memory/write", json=payload, timeout=10)
    print(f"  Status: {r.status_code}")
    if r.status_code in [200, 201]:
        print(f"  Response: {r.json()}")
    else:
        print(f"  Error: {r.text[:200]}")
except Exception as e:
    print(f"  ERROR: {e}")

# Test security audit
print("\nTesting Security Audit Log:")
try:
    payload = {
        "user_id": "test_user",
        "action": "memory_verification",
        "resource": "integration_test",
        "details": {"verified": True},
        "success": True,
        "severity": "info"
    }
    r = requests.post(f"{MAS_URL}/api/security/audit/log", json=payload, timeout=10)
    print(f"  Status: {r.status_code}")
    if r.status_code in [200, 201]:
        print(f"  Entry logged: {r.json().get('entry_id', 'OK')}")
    else:
        print(f"  Error: {r.text[:200]}")
except Exception as e:
    print(f"  ERROR: {e}")

# Test security stats
print("\nTesting Security Stats:")
try:
    r = requests.get(f"{MAS_URL}/api/security/audit/stats", timeout=10)
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        stats = r.json()
        print(f"  Total entries: {stats.get('total_entries', 0)}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n" + "=" * 50)
print("Verification complete!")
