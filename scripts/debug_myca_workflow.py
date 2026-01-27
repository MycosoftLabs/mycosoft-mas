#!/usr/bin/env python3
"""Debug MYCA Command API workflow - January 27, 2026"""
import requests
import json

N8N_URL = "http://192.168.0.188:5678"
N8N_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1YTYxMTEyYS00YWViLTQwYTItYTUwNC1iZDY3YWZhOGU1NWIiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY5NTM4NzM0LCJleHAiOjE3NzIwOTI4MDB9.I1mgswouNspryGfJfIiVz-tOhW0iBQg5f0OfJbwxWvw"

headers = {"X-N8N-API-KEY": N8N_API_KEY}

# Get MYCA Command API workflow
print("=== MYCA Command API Full Debug ===\n")
r = requests.get(f"{N8N_URL}/api/v1/workflows/cHsJEUEhpedSOuk3", headers=headers, timeout=10)
details = r.json()

print(f"Workflow: {details.get('name')}")
print()

nodes = details.get("nodes", [])
for node in nodes:
    print(f"Node: {node.get('name')}")
    print(f"  Type: {node.get('type')}")
    
    # Check for credentials
    creds = node.get("credentials")
    if creds:
        print(f"  Credentials: {json.dumps(creds)}")
    
    # Check parameters for any auth-related fields
    params = node.get("parameters", {})
    auth_keys = [k for k in params.keys() if 'auth' in k.lower() or 'cred' in k.lower() or 'api' in k.lower()]
    if auth_keys:
        print(f"  Auth-related params: {auth_keys}")
    
    # Check for authentication field
    auth = params.get("authentication") or params.get("authType") or params.get("auth")
    if auth:
        print(f"  Authentication: {auth}")
    
    print()

# Also list all executions to see recent errors
print("=== Recent Executions ===")
r = requests.get(f"{N8N_URL}/api/v1/executions?workflowId=cHsJEUEhpedSOuk3&limit=3", headers=headers, timeout=10)
execs = r.json().get("data", [])
for ex in execs:
    print(f"  ID: {ex.get('id')} Status: {ex.get('status')} Mode: {ex.get('mode')}")
