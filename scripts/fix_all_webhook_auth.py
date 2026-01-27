#!/usr/bin/env python3
"""Fix all n8n webhook auth - January 27, 2026
Remove headerAuth from all active workflows with webhooks
"""
import requests
import json
from datetime import datetime

N8N_URL = "http://192.168.0.188:5678"
N8N_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1YTYxMTEyYS00YWViLTQwYTItYTUwNC1iZDY3YWZhOGU1NWIiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY5NTM4NzM0LCJleHAiOjE3NzIwOTI4MDB9.I1mgswouNspryGfJfIiVz-tOhW0iBQg5f0OfJbwxWvw"

headers = {"X-N8N-API-KEY": N8N_API_KEY, "Content-Type": "application/json"}

def log(msg, status="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    symbols = {"INFO": "[i]", "OK": "[+]", "WARN": "[!]", "ERR": "[X]"}
    print(f"[{ts}] {symbols.get(status, '*')} {msg}")

def fix_workflow(workflow_id, workflow_name):
    """Fix webhook auth in a workflow"""
    try:
        # Get workflow details
        r = requests.get(f"{N8N_URL}/api/v1/workflows/{workflow_id}", headers=headers, timeout=10)
        if r.status_code != 200:
            return False, "Failed to get workflow"
        
        workflow = r.json()
        nodes = workflow.get("nodes", [])
        
        # Find webhooks with auth
        updated = False
        for node in nodes:
            if node.get("type") == "n8n-nodes-base.webhook":
                params = node.get("parameters", {})
                auth = params.get("authentication")
                if auth and auth != "none":
                    params["authentication"] = "none"
                    if "credentials" in node:
                        del node["credentials"]
                    updated = True
        
        if not updated:
            return True, "No auth changes needed"
        
        # Deactivate
        requests.post(f"{N8N_URL}/api/v1/workflows/{workflow_id}/deactivate", headers=headers, timeout=10)
        
        # Update
        update_data = {
            "name": workflow.get("name"),
            "nodes": nodes,
            "connections": workflow.get("connections", {}),
            "settings": workflow.get("settings", {}),
        }
        r = requests.put(f"{N8N_URL}/api/v1/workflows/{workflow_id}", headers=headers, json=update_data, timeout=10)
        if r.status_code != 200:
            return False, f"Update failed: {r.status_code}"
        
        # Reactivate
        requests.post(f"{N8N_URL}/api/v1/workflows/{workflow_id}/activate", headers=headers, timeout=10)
        
        return True, "Fixed and reactivated"
    
    except Exception as e:
        return False, str(e)

print("=" * 60)
print("FIX ALL n8n WEBHOOK AUTH")
print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# Get all active workflows
r = requests.get(f"{N8N_URL}/api/v1/workflows", headers=headers, timeout=10)
workflows = r.json().get("data", [])

active_workflows = [w for w in workflows if w.get("active")]
log(f"Found {len(active_workflows)} active workflows")

fixed = 0
for wf in active_workflows:
    wid = wf.get("id")
    name = wf.get("name")
    success, msg = fix_workflow(wid, name)
    if "Fixed" in msg:
        log(f"{name}: {msg}", "OK")
        fixed += 1
    elif success:
        log(f"{name}: {msg}", "INFO")
    else:
        log(f"{name}: {msg}", "ERR")

print()
log(f"Fixed {fixed} workflows", "OK")

# Now test the webhooks
print()
print("=" * 60)
print("TESTING WEBHOOKS")
print("=" * 60)

webhooks_to_test = [
    "/webhook/myca/command",
    "/webhook/myca-chat",
]

for path in webhooks_to_test:
    try:
        r = requests.post(f"{N8N_URL}{path}", json={"message": "test", "action": "health"}, timeout=10)
        status = "OK" if r.status_code in [200, 201] else ("ERR" if r.status_code >= 500 else "WARN")
        log(f"{path}: {r.status_code}", status)
    except Exception as e:
        log(f"{path}: {e}", "ERR")
