"""Test n8n API access with different auth methods"""
import requests
from requests.auth import HTTPBasicAuth

N8N_URL = "http://localhost:5678"

# Try basic auth
print("Testing Basic Auth...")
auth = HTTPBasicAuth("morgan@mycosoft.org", "Mushroom1!Mushroom1!")

try:
    r = requests.get(f"{N8N_URL}/api/v1/workflows", auth=auth, timeout=10)
    print(f"Basic Auth Status: {r.status_code}")
    if r.status_code == 200:
        workflows = r.json().get("data", [])
        print(f"Found {len(workflows)} workflows")
    else:
        print(r.text[:200])
except Exception as e:
    print(f"Error: {e}")

# Try without auth (public API mode)
print("\nTesting No Auth...")
try:
    r = requests.get(f"{N8N_URL}/api/v1/workflows", timeout=10)
    print(f"No Auth Status: {r.status_code}")
    if r.status_code == 200:
        workflows = r.json().get("data", [])
        print(f"Found {len(workflows)} workflows")
    else:
        print(r.text[:200])
except Exception as e:
    print(f"Error: {e}")

# Check if n8n has public API enabled
print("\nChecking n8n settings...")
try:
    r = requests.get(f"{N8N_URL}/", timeout=10)
    print(f"Root endpoint: {r.status_code}")
except Exception as e:
    print(f"Error: {e}")
