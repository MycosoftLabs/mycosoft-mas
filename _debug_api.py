#!/usr/bin/env python3
"""Debug API issues."""

import requests

MAS_URL = "http://192.168.0.188:8001"

print("Checking available API routes...")

try:
    r = requests.get(f"{MAS_URL}/openapi.json", timeout=15)
    if r.status_code == 200:
        spec = r.json()
        paths = spec.get("paths", {})
        
        # Group by category
        memory_paths = [p for p in paths.keys() if "memory" in p.lower()]
        voice_paths = [p for p in paths.keys() if "voice" in p.lower()]
        mindex_paths = [p for p in paths.keys() if "mindex" in p.lower()]
        natureos_paths = [p for p in paths.keys() if "natureos" in p.lower()]
        workflow_paths = [p for p in paths.keys() if "workflow" in p.lower()]
        security_paths = [p for p in paths.keys() if "security" in p.lower()]
        
        print(f"\nMemory endpoints ({len(memory_paths)}):")
        for p in sorted(memory_paths):
            print(f"  {p}")
        
        print(f"\nVoice endpoints ({len(voice_paths)}):")
        for p in sorted(voice_paths):
            print(f"  {p}")
        
        print(f"\nMINDEX endpoints ({len(mindex_paths)}):")
        for p in sorted(mindex_paths):
            print(f"  {p}")
        
        print(f"\nNatureOS endpoints ({len(natureos_paths)}):")
        for p in sorted(natureos_paths):
            print(f"  {p}")
        
        print(f"\nWorkflow endpoints ({len(workflow_paths)}):")
        for p in sorted(workflow_paths):
            print(f"  {p}")
        
        print(f"\nSecurity endpoints ({len(security_paths)}):")
        for p in sorted(security_paths):
            print(f"  {p}")
            
        print(f"\nTotal endpoints: {len(paths)}")
    else:
        print(f"Failed to get OpenAPI: {r.status_code}")
except Exception as e:
    print(f"Error: {e}")

# Test specific endpoints
print("\n" + "=" * 50)
print("Testing specific endpoints:")
print("=" * 50)

endpoints = [
    ("GET", "/health"),
    ("GET", "/api/memory/health"),
    ("POST", "/api/voice/session/create"),
    ("GET", "/mindex/health"),
    ("POST", "/api/natureos/telemetry/store"),
    ("POST", "/api/workflows/memory/archive"),
]

for method, path in endpoints:
    try:
        if method == "GET":
            r = requests.get(f"{MAS_URL}{path}", timeout=10)
        else:
            r = requests.post(f"{MAS_URL}{path}", json={}, timeout=10)
        print(f"  {method} {path}: {r.status_code}")
    except Exception as e:
        print(f"  {method} {path}: ERROR - {e}")
