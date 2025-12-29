#!/usr/bin/env python3
"""Complete MycoBrain device test"""
import requests
import time

SERVICE = "http://localhost:8003"
PORT = "COM6"
DEVICE_ID = f"mycobrain-{PORT}"

print("\n" + "="*70)
print("MycoBrain Complete Device Test Suite")
print("="*70 + "\n")

# Connect
print("1. Connecting to COM6...")
try:
    r = requests.post(f"{SERVICE}/devices/connect/{PORT}", json={"port": PORT, "baudrate": 115200}, timeout=10)
    if r.status_code == 200:
        print(f"   OK - {r.json().get('device_id')}")
    else:
        print(f"   FAIL - {r.json().get('detail')}")
        exit(1)
except Exception as e:
    print(f"   ERROR - {e}")
    exit(1)

time.sleep(1)

# Status
print("\n2. Device Status...")
try:
    r = requests.get(f"{SERVICE}/devices/{DEVICE_ID}/status", timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"   OK - Status: {data.get('status')}, Port: {data.get('port')}")
    else:
        print(f"   FAIL - {r.status_code}: {r.text[:100]}")
except Exception as e:
    print(f"   ERROR - {e}")

time.sleep(0.5)

# Ping
print("\n3. Ping Command...")
try:
    r = requests.post(f"{SERVICE}/devices/{DEVICE_ID}/command", json={"command": {"cmd": "ping"}}, timeout=10)
    if r.status_code == 200:
        print(f"   OK - Status: {r.json().get('status')}")
    else:
        print(f"   FAIL - {r.status_code}")
except Exception as e:
    print(f"   ERROR - {e}")

time.sleep(0.5)

# LED ON
print("\n4. LED ON (Red)...")
try:
    r = requests.post(f"{SERVICE}/devices/{DEVICE_ID}/command", json={"command": {"cmd": "led", "action": "on", "color": [255, 0, 0], "brightness": 128}}, timeout=10)
    if r.status_code == 200:
        print(f"   OK - Command sent")
    else:
        print(f"   FAIL - {r.status_code}")
except Exception as e:
    print(f"   ERROR - {e}")

time.sleep(1)

# LED OFF
print("\n5. LED OFF...")
try:
    r = requests.post(f"{SERVICE}/devices/{DEVICE_ID}/command", json={"command": {"cmd": "led", "action": "off"}}, timeout=10)
    if r.status_code == 200:
        print(f"   OK - Command sent")
    else:
        print(f"   FAIL - {r.status_code}")
except Exception as e:
    print(f"   ERROR - {e}")

time.sleep(0.5)

# Buzzer
print("\n6. Buzzer ON...")
try:
    r = requests.post(f"{SERVICE}/devices/{DEVICE_ID}/command", json={"command": {"cmd": "buzzer", "action": "on", "frequency": 1000, "duration": 300}}, timeout=10)
    if r.status_code == 200:
        print(f"   OK - Command sent (should beep)")
    else:
        print(f"   FAIL - {r.status_code}")
except Exception as e:
    print(f"   ERROR - {e}")

time.sleep(0.5)

# Sensors
print("\n7. Sensor Reading...")
try:
    r = requests.post(f"{SERVICE}/devices/{DEVICE_ID}/command", json={"command": {"cmd": "get_sensors"}}, timeout=10)
    if r.status_code == 200:
        data = r.json()
        print(f"   OK - Status: {data.get('status')}")
        if data.get('response'):
            print(f"   Response: {data.get('response')[:150]}")
    else:
        print(f"   FAIL - {r.status_code}")
except Exception as e:
    print(f"   ERROR - {e}")

time.sleep(0.5)

# Telemetry
print("\n8. Telemetry...")
try:
    r = requests.get(f"{SERVICE}/devices/{DEVICE_ID}/telemetry", timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"   OK - Status: {data.get('status')}")
        if data.get('telemetry'):
            print(f"   Data: {data.get('telemetry')}")
    else:
        print(f"   FAIL - {r.status_code}")
except Exception as e:
    print(f"   ERROR - {e}")

print("\n" + "="*70)
print("All tests completed!")
print("="*70 + "\n")




