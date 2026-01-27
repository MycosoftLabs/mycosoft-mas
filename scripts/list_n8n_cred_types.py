#!/usr/bin/env python3
"""List n8n credential types"""
import requests

N8N_URL = "http://192.168.0.188:5678"
N8N_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1YTYxMTEyYS00YWViLTQwYTItYTUwNC1iZDY3YWZhOGU1NWIiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY5NTM4NzM0LCJleHAiOjE3NzIwOTI4MDB9.I1mgswouNspryGfJfIiVz-tOhW0iBQg5f0OfJbwxWvw"
headers = {"X-N8N-API-KEY": N8N_API_KEY}

# Get credential types via schema endpoint
r = requests.get(f"{N8N_URL}/api/v1/credentials/schema/openAiApi", headers=headers, timeout=10)
print(f"OpenAI schema: {r.status_code}")
if r.ok:
    print(r.json())

# Try httpHeaderAuth which worked
r = requests.get(f"{N8N_URL}/api/v1/credentials/schema/httpHeaderAuth", headers=headers, timeout=10)
print(f"\nhttpHeaderAuth schema: {r.status_code}")
if r.ok:
    data = r.json()
    print(f"Properties: {list(data.get('properties', {}).keys())}")
