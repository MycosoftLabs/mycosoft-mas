#!/usr/bin/env python3
"""Check n8n workflows and webhook status - January 27, 2026"""
import requests
import os
import json
import os

N8N_URL = "http://192.168.0.188:5678"
N8N_API_KEY = os.getenv("N8N_API_KEY", "")

headers = {"X-N8N-API-KEY": N8N_API_KEY}

print("=== n8n Workflow Status ===")
r = requests.get(f"{N8N_URL}/api/v1/workflows", headers=headers, timeout=10)
data = r.json().get("data", [])
print(f"Total workflows: {len(data)}")
print()

active = [w for w in data if w.get("active")]
print(f"Active workflows ({len(active)}):")
for w in active:
    name = w.get("name", "Unknown")
    wid = w.get("id", "")
    print(f"  [{wid}] {name}")

print()
print("=== Testing Webhook ===")
# Test the myca/command webhook with verbose output
r = requests.post(
    f"{N8N_URL}/webhook/myca/command",
    json={"message": "hello", "action": "test"},
    timeout=15
)
print(f"Status: {r.status_code}")
print(f"Response: {r.text[:500]}")

# Find MYCA Command API workflow and check details
print()
print("=== MYCA Command API Workflow Details ===")
myca_command = next((w for w in data if "Command API" in w.get("name", "")), None)
if myca_command:
    wid = myca_command.get("id")
    r = requests.get(f"{N8N_URL}/api/v1/workflows/{wid}", headers=headers, timeout=10)
    details = r.json()
    
    print(f"Name: {details.get('name')}")
    print(f"Active: {details.get('active')}")
    
    # Find webhook node
    for node in details.get("nodes", []):
        if node.get("type") == "n8n-nodes-base.webhook":
            print(f"Webhook path: {node.get('parameters', {}).get('path')}")
        
        # Check for credentials in other nodes
        creds = node.get("credentials")
        if creds:
            print(f"Node '{node.get('name')}' uses credentials: {list(creds.keys())}")
