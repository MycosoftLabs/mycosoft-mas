"""Test the PersonaPlex bridge text endpoint."""

import requests
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BRIDGE_URL = "http://localhost:8999"
MAS_URL = "http://192.168.0.188:8001"
WEBSITE_URL = "http://localhost:3010"

print("=" * 70)
print("PersonaPlex Bridge and Voice Flow Test")
print("=" * 70)

# Test 1: Direct MAS VM
print("\n1. Testing direct MAS VM (192.168.0.188:8001)...")
try:
    response = requests.post(
        f"{MAS_URL}/voice/orchestrator/chat",
        json={"message": "Hello, who are you?"},
        timeout=30
    )
    if response.ok:
        data = response.json()
        print(f"   [OK] MAS VM Response: {data.get('response_text', 'No response')[:100]}...")
    else:
        print(f"   [FAIL] Error: {response.status_code}")
except Exception as e:
    print(f"   [FAIL] Exception: {e}")

# Test 2: Through Website
print("\n2. Testing through website (localhost:3010)...")
try:
    response = requests.post(
        f"{WEBSITE_URL}/api/mas/voice/orchestrator",
        json={"message": "What is Mycosoft building?"},
        timeout=30
    )
    if response.ok:
        data = response.json()
        print(f"   [OK] Website Response: {data.get('response_text', data.get('response', 'No response'))[:100]}...")
    else:
        print(f"   [FAIL] Error: {response.status_code} - {response.text[:100]}")
except Exception as e:
    print(f"   [FAIL] Exception: {e}")

# Test 3: Bridge health
print("\n3. Testing PersonaPlex bridge health (localhost:8999)...")
try:
    response = requests.get(f"{BRIDGE_URL}/health", timeout=10)
    if response.ok:
        print(f"   [OK] Bridge Health: {response.json()}")
    else:
        print(f"   [FAIL] Error: {response.status_code}")
except Exception as e:
    print(f"   [FAIL] Exception: {e}")

# Test 4: Moshi server
print("\n4. Testing Moshi server (localhost:8998)...")
try:
    response = requests.get("http://localhost:8998/", timeout=10)
    if response.ok:
        print(f"   [OK] Moshi Server: Running (status {response.status_code})")
    else:
        print(f"   [WARN] Moshi Server: {response.status_code}")
except Exception as e:
    print(f"   [FAIL] Exception: {e}")

print("\n" + "=" * 70)
print("Full Voice Flow Test Complete")
print("=" * 70)
print("""
TO TEST VOICE:
  1. Open http://localhost:8998 in your browser
  2. Paste the MYCA prompt from config/myca_personaplex_prompt_1000.txt
  3. Select voice: NATURAL_F2
  4. Click Connect
  5. Allow microphone
  6. Ask: "What is your name?" or "Tell me about Mycosoft"
  
The conversation should be natural, full-duplex, and MYCA should
know all about Mycosoft, science, agents, devices, and plans.
""")
