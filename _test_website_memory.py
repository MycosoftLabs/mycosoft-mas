#!/usr/bin/env python3
"""Test website memory dashboard and API integration."""

import requests
import json
from datetime import datetime

WEBSITE_URL = "http://localhost:3010"
MAS_URL = "http://192.168.0.188:8001"

def log_test(name: str, status: str, details: str = ""):
    icon = {"PASS": "[PASS]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}[status]
    print(f"{icon} {name}: {details}")

print("=" * 70)
print("  MYCOSOFT WEBSITE MEMORY DASHBOARD TEST")
print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
print("=" * 70)

# Test 1: Website health
print("\n--- Website Availability ---")
try:
    r = requests.get(f"{WEBSITE_URL}/", timeout=10)
    if r.status_code == 200:
        log_test("Website Home", "PASS", f"Status: {r.status_code}")
    else:
        log_test("Website Home", "FAIL", f"Status: {r.status_code}")
except Exception as e:
    log_test("Website Home", "FAIL", str(e))

# Test 2: AI Studio page
print("\n--- AI Studio Page ---")
try:
    r = requests.get(f"{WEBSITE_URL}/natureos/ai-studio", timeout=15)
    if r.status_code == 200:
        log_test("AI Studio Page", "PASS", f"Status: {r.status_code}")
        # Check if Memory tab components are present
        if "Memory" in r.text or "memory" in r.text:
            log_test("Memory Tab in HTML", "PASS", "Memory references found")
        else:
            log_test("Memory Tab in HTML", "SKIP", "Memory not in initial HTML (CSR)")
    else:
        log_test("AI Studio Page", "FAIL", f"Status: {r.status_code}")
except Exception as e:
    log_test("AI Studio Page", "FAIL", str(e))

# Test 3: Topology page
print("\n--- Topology Page ---")
try:
    r = requests.get(f"{WEBSITE_URL}/natureos/mas/topology", timeout=15)
    if r.status_code == 200:
        log_test("Topology Page", "PASS", f"Status: {r.status_code}")
    else:
        log_test("Topology Page", "FAIL", f"Status: {r.status_code}")
except Exception as e:
    log_test("Topology Page", "FAIL", str(e))

# Test 4: MAS Memory API (direct)
print("\n--- MAS Memory API (Direct) ---")
try:
    r = requests.get(f"{MAS_URL}/api/memory/health", timeout=10)
    if r.status_code == 200:
        data = r.json()
        log_test("MAS Memory Health", "PASS", f"Status: {data.get('status')}, Redis: {data.get('redis')}")
    else:
        log_test("MAS Memory Health", "FAIL", f"Status: {r.status_code}")
except Exception as e:
    log_test("MAS Memory Health", "FAIL", str(e))

# Test 5: Write memory via MAS API
print("\n--- Memory Write Test ---")
try:
    payload = {
        "scope": "user",
        "namespace": "test_dashboard",
        "key": "test_entry",
        "value": {"tested_at": datetime.utcnow().isoformat(), "source": "website_test"},
        "source": "website-memory-dashboard"
    }
    r = requests.post(f"{MAS_URL}/api/memory/write", json=payload, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("success"):
            log_test("Memory Write", "PASS", "Entry written successfully")
        else:
            log_test("Memory Write", "FAIL", f"Response: {data}")
    else:
        log_test("Memory Write", "FAIL", f"Status: {r.status_code}")
except Exception as e:
    log_test("Memory Write", "FAIL", str(e))

# Test 6: Read memory via MAS API
print("\n--- Memory Read Test ---")
try:
    payload = {
        "scope": "user",
        "namespace": "test_dashboard",
        "key": "test_entry"
    }
    r = requests.post(f"{MAS_URL}/api/memory/read", json=payload, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("success") and data.get("value"):
            log_test("Memory Read", "PASS", f"Retrieved value with source: {data['value'].get('source', 'N/A')}")
        else:
            log_test("Memory Read", "FAIL", f"Response: {data}")
    else:
        log_test("Memory Read", "FAIL", f"Status: {r.status_code}")
except Exception as e:
    log_test("Memory Read", "FAIL", str(e))

# Test 7: List memory entries
print("\n--- Memory List Test ---")
try:
    r = requests.get(f"{MAS_URL}/api/memory/list/user/test_dashboard", timeout=10)
    if r.status_code == 200:
        data = r.json()
        log_test("Memory List", "PASS", f"Found {data.get('count', 0)} entries")
    else:
        log_test("Memory List", "FAIL", f"Status: {r.status_code}")
except Exception as e:
    log_test("Memory List", "FAIL", str(e))

# Test 8: Security Audit API
print("\n--- Security Audit API ---")
try:
    r = requests.get(f"{MAS_URL}/api/security/audit/query?limit=5", timeout=10)
    if r.status_code == 200:
        data = r.json()
        log_test("Audit Query", "PASS", f"Retrieved {len(data.get('entries', []))} entries")
    else:
        log_test("Audit Query", "FAIL", f"Status: {r.status_code}")
except Exception as e:
    log_test("Audit Query", "FAIL", str(e))

# Test 9: All 8 memory scopes
print("\n--- All Memory Scopes ---")
scopes = ["conversation", "user", "agent", "system", "ephemeral", "device", "experiment", "workflow"]
scope_results = {}
for scope in scopes:
    try:
        payload = {
            "scope": scope,
            "namespace": "dashboard_test",
            "key": f"scope_test_{scope}",
            "value": {"scope": scope, "tested": datetime.utcnow().isoformat()},
            "source": "scope-test"
        }
        r = requests.post(f"{MAS_URL}/api/memory/write", json=payload, timeout=10)
        if r.status_code == 200 and r.json().get("success"):
            scope_results[scope] = "PASS"
            log_test(f"Scope: {scope}", "PASS", "Write successful")
        else:
            scope_results[scope] = "FAIL"
            log_test(f"Scope: {scope}", "FAIL", f"Status: {r.status_code}")
    except Exception as e:
        scope_results[scope] = "FAIL"
        log_test(f"Scope: {scope}", "FAIL", str(e))

# Test 10: Voice Session API
print("\n--- Voice Session API ---")
try:
    payload = {
        "session_id": "dashboard_voice_test",
        "conversation_id": "conv_test",
        "mode": "personaplex",
        "persona": "myca"
    }
    r = requests.post(f"{MAS_URL}/api/voice/session/create", json=payload, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("success"):
            log_test("Voice Session", "PASS", f"Session: {data.get('session_id')}")
        else:
            log_test("Voice Session", "FAIL", f"Response: {data}")
    else:
        log_test("Voice Session", "FAIL", f"Status: {r.status_code}")
except Exception as e:
    log_test("Voice Session", "FAIL", str(e))

# Test 11: MINDEX Health
print("\n--- MINDEX Integration ---")
try:
    r = requests.get(f"{MAS_URL}/mindex/health", timeout=10)
    if r.status_code == 200:
        data = r.json()
        log_test("MINDEX Health", "PASS", f"Status: {data.get('status')}")
    else:
        log_test("MINDEX Health", "FAIL", f"Status: {r.status_code}")
except Exception as e:
    log_test("MINDEX Health", "FAIL", str(e))

# Test 12: NatureOS Telemetry
print("\n--- NatureOS Integration ---")
try:
    payload = {
        "device_id": "dashboard_device_test",
        "device_type": "mushroom1",
        "readings": {"temperature": 25.5, "humidity": 85.0, "co2": 450}
    }
    r = requests.post(f"{MAS_URL}/api/natureos/telemetry/store", json=payload, timeout=10)
    if r.status_code == 200:
        data = r.json()
        if data.get("success"):
            log_test("NatureOS Telemetry", "PASS", f"Device: {data.get('device_id')}")
        else:
            log_test("NatureOS Telemetry", "FAIL", f"Response: {data}")
    else:
        log_test("NatureOS Telemetry", "FAIL", f"Status: {r.status_code}")
except Exception as e:
    log_test("NatureOS Telemetry", "FAIL", str(e))

# Summary
print("\n" + "=" * 70)
passed = sum(1 for s in scope_results.values() if s == "PASS")
print(f"  SCOPE TEST SUMMARY: {passed}/8 scopes working")
print("=" * 70)

# Save results
results = {
    "timestamp": datetime.utcnow().isoformat(),
    "website_url": WEBSITE_URL,
    "mas_url": MAS_URL,
    "scope_results": scope_results,
    "tests_passed": passed
}

with open("tests/website_memory_test_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("\nResults saved to: tests/website_memory_test_results.json")
