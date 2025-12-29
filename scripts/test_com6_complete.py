#!/usr/bin/env python3
"""Complete test of COM6 MycoBrain device"""
import requests
import time
import json

SERVICE_URL = "http://localhost:8003"
PORT = "COM6"
DEVICE_ID = f"mycobrain-{PORT}"

print("\n" + "="*70)
print("MycoBrain Device Complete Test Suite - COM6")
print("="*70 + "\n")

# Connect
print("1. Connecting to device...")
try:
    r = requests.post(f"{SERVICE_URL}/devices/connect/{PORT}", json={"port": PORT, "baudrate": 115200}, timeout=10)
    if r.status_code == 200:
        data = r.json()
        print(f"   OK - Connected: {data.get('device_id')}")
    else:
        print(f"   FAIL - {r.json().get('detail')}")
        exit(1)
except Exception as e:
    print(f"   ERROR - {e}")
    exit(1)

time.sleep(1)

# Test Status
print("\n2. Testing device status...")
try:
    r = requests.get(f"{SERVICE_URL}/devices/{DEVICE_ID}/status", timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"   OK - Status: {data.get('status')}, Port: {data.get('port')}")
    else:
        print(f"   FAIL - {r.status_code}: {r.text}")
except Exception as e:
    print(f"   ERROR - {e}")

# Test Ping
print("\n3. Testing ping command...")
try:
    r = requests.post(f"{SERVICE_URL}/devices/{DEVICE_ID}/command", json={"command": {"cmd": "ping"}}, timeout=10)
    if r.status_code == 200:
        data = r.json()
        print(f"   OK - Ping sent, Status: {data.get('status')}")
        if data.get('response'):
            print(f"   Response: {data.get('response')[:100]}")
    else:
        print(f"   FAIL - {r.status_code}")
except Exception as e:
    print(f"   ERROR - {e}")

time.sleep(0.5)

# Test LED ON
print("\n4. Testing LED control (Red ON)...")
try:
    r = requests.post(f"{SERVICE_URL}/devices/{DEVICE_ID}/command", json={"command": {"cmd": "led", "action": "on", "color": [255, 0, 0], "brightness": 128}}, timeout=10)
    if r.status_code == 200:
        print(f"   OK - LED ON command sent")
    else:
        print(f"   FAIL - {r.status_code}")
except Exception as e:
    print(f"   ERROR - {e}")

time.sleep(1)

# Test LED OFF
print("\n5. Testing LED control (OFF)...")
try:
    r = requests.post(f"{SERVICE_URL}/devices/{DEVICE_ID}/command", json={"command": {"cmd": "led", "action": "off"}}, timeout=10)
    if r.status_code == 200:
        print(f"   OK - LED OFF command sent")
    else:
        print(f"   FAIL - {r.status_code}")
except Exception as e:
    print(f"   ERROR - {e}")

time.sleep(0.5)

# Test Buzzer
print("\n6. Testing buzzer control...")
try:
    r = requests.post(f"{SERVICE_URL}/devices/{DEVICE_ID}/command", json={"command": {"cmd": "buzzer", "action": "on", "frequency": 1000, "duration": 300}}, timeout=10)
    if r.status_code == 200:
        print(f"   OK - Buzzer ON command sent (should beep for 300ms)")
    else:
        print(f"   FAIL - {r.status_code}")
except Exception as e:
    print(f"   ERROR - {e}")

time.sleep(0.5)

# Test Sensors
print("\n7. Testing sensor reading...")
try:
    r = requests.post(f"{SERVICE_URL}/devices/{DEVICE_ID}/command", json={"command": {"cmd": "get_sensors", "sensors": ["temperature", "humidity", "pressure", "gas"]}}, timeout=10)
    if r.status_code == 200:
        data = r.json()
        print(f"   OK - Sensor command sent, Status: {data.get('status')}")
        response = data.get('response')
        if response:
            print(f"   Response: {response[:200]}")
        else:
            print(f"   NOTE - No response data (device may not have responded)")
    else:
        print(f"   FAIL - {r.status_code}")
except Exception as e:
    print(f"   ERROR - {e}")

time.sleep(0.5)

# Test Telemetry
print("\n8. Testing telemetry retrieval...")
try:
    r = requests.get(f"{SERVICE_URL}/devices/{DEVICE_ID}/telemetry", timeout=5)
    if r.status_code == 200:
        data = r.json()
        status = data.get('status')
        print(f"   OK - Telemetry request, Status: {status}")
        if status == "ok":
            telemetry = data.get('telemetry', {})
            print(f"   Telemetry data: {telemetry}")
        else:
            print(f"   NOTE - {data.get('message', 'No telemetry data')}")
    else:
        print(f"   FAIL - {r.status_code}")
except Exception as e:
    print(f"   ERROR - {e}")

print("\n" + "="*70)
print("All interaction tests completed!")
print("="*70 + "\n")






