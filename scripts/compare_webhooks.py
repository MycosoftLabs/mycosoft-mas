#!/usr/bin/env python3
"""Compare n8n webhook configurations"""
import requests
import json

N8N_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1YTYxMTEyYS00YWViLTQwYTItYTUwNC1iZDY3YWZhOGU1NWIiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY5NTM4NzM0LCJleHAiOjE3NzIwOTI4MDB9.I1mgswouNspryGfJfIiVz-tOhW0iBQg5f0OfJbwxWvw"
N8N_URL = "http://192.168.0.188:5678"
headers = {"X-N8N-API-KEY": N8N_API_KEY}

# Compare webhook nodes from Command API (working) vs Speech Complete (not working)
workflows = {
    "cHsJEUEhpedSOuk3": "MYCA Command API",
    "kzqcePJDjwyDwnqE": "MYCA Speech Complete"
}

for wf_id, name in workflows.items():
    r = requests.get(f"{N8N_URL}/api/v1/workflows/{wf_id}", headers=headers)
    data = r.json()
    print(f"\n=== {name} ===")
    print(f"Active: {data.get('active')}")
    for node in data.get("nodes", []):
        if node.get("type") == "n8n-nodes-base.webhook":
            print(f"Webhook Node: {node.get('name')}")
            print(f"  typeVersion: {node.get('typeVersion')}")
            params = node.get("parameters", {})
            print(f"  path: {params.get('path')}")
            print(f"  httpMethod: {params.get('httpMethod')}")
            print(f"  responseMode: {params.get('responseMode')}")
