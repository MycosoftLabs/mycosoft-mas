"""Test MINDEX unified search."""
import requests
import json

MINDEX_URL = "http://192.168.0.189:8000"

def test_search(query: str):
    url = f"{MINDEX_URL}/api/mindex/unified-search?q={query}&limit=5"
    print(f"Testing: {url}")
    try:
        r = requests.get(url, timeout=30)
        print(f"Status: {r.status_code}")
        data = r.json()
        print(f"Response: {json.dumps(data, indent=2, default=str)[:2000]}")
        return data
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    test_search("Amanita")
