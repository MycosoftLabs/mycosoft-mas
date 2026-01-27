#!/usr/bin/env python3
"""Fix MYCA Command API webhook auth - January 27, 2026
Remove the headerAuth requirement so the webhook works without credentials
"""
import requests
import json

N8N_URL = "http://192.168.0.188:5678"
N8N_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1YTYxMTEyYS00YWViLTQwYTItYTUwNC1iZDY3YWZhOGU1NWIiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY5NTM4NzM0LCJleHAiOjE3NzIwOTI4MDB9.I1mgswouNspryGfJfIiVz-tOhW0iBQg5f0OfJbwxWvw"

headers = {"X-N8N-API-KEY": N8N_API_KEY, "Content-Type": "application/json"}
WORKFLOW_ID = "cHsJEUEhpedSOuk3"

print("=== Fixing MYCA Command API Webhook Auth ===\n")

# Get current workflow
r = requests.get(f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}", headers=headers, timeout=10)
workflow = r.json()

print(f"Workflow: {workflow.get('name')}")
print(f"Current active: {workflow.get('active')}")

# Find and update the webhook node
nodes = workflow.get("nodes", [])
updated = False
for node in nodes:
    if node.get("type") == "n8n-nodes-base.webhook":
        params = node.get("parameters", {})
        current_auth = params.get("authentication")
        print(f"\nWebhook node: {node.get('name')}")
        print(f"Current auth: {current_auth}")
        
        if current_auth and current_auth != "none":
            # Remove authentication
            params["authentication"] = "none"
            # Remove any credential reference
            if "credentials" in node:
                del node["credentials"]
            updated = True
            print(f"Changed auth to: none")

if updated:
    # Deactivate first
    print("\nDeactivating workflow...")
    r = requests.post(f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}/deactivate", headers=headers, timeout=10)
    print(f"Deactivate: {r.status_code}")
    
    # Update workflow
    print("Updating workflow...")
    update_data = {
        "name": workflow.get("name"),
        "nodes": nodes,
        "connections": workflow.get("connections", {}),
        "settings": workflow.get("settings", {}),
    }
    r = requests.put(f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}", headers=headers, json=update_data, timeout=10)
    print(f"Update: {r.status_code}")
    if r.status_code != 200:
        print(f"Error: {r.text[:200]}")
    
    # Reactivate
    print("Reactivating workflow...")
    r = requests.post(f"{N8N_URL}/api/v1/workflows/{WORKFLOW_ID}/activate", headers=headers, timeout=10)
    print(f"Activate: {r.status_code}")
    
    # Test webhook
    print("\nTesting webhook...")
    r = requests.post(f"{N8N_URL}/webhook/myca/command", json={"message": "test"}, timeout=15)
    print(f"Webhook test: {r.status_code}")
    print(f"Response: {r.text[:200]}")
else:
    print("\nNo auth changes needed")
