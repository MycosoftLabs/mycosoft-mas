#!/usr/bin/env python3
"""Complete test of MycoBrain device through sandbox website"""

import requests
import json
import time

print("=" * 80)
print("COMPLETE MYCOBRAIN DEVICE TEST")
print("=" * 80)

# Test endpoints
sandbox_base = "https://sandbox.mycosoft.com"
local_base = "http://localhost:3000"

def test_endpoint(name, url, method="GET", data=None):
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=data, timeout=10)
        
        status = "OK" if response.status_code == 200 else f"HTTP {response.status_code}"
        print(f"  {name:40s} {status}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                return result
            except:
                return {"raw": response.text[:100]}
        else:
            return {"error": response.status_code}
    except Exception as e:
        print(f"  {name:40s} ERROR: {str(e)[:50]}")
        return None

print("\n[TEST 1] Testing Sandbox Website Endpoints...")
print("-" * 80)

# Device detection
test_endpoint("Sandbox: /api/mycobrain/devices", f"{sandbox_base}/api/mycobrain/devices")
test_endpoint("Sandbox: /api/mycobrain/ports", f"{sandbox_base}/api/mycobrain/ports")

print("\n[TEST 2] Testing Local Website Endpoints...")
print("-" * 80)

devices = test_endpoint("Local: /api/mycobrain/devices", f"{local_base}/api/mycobrain/devices")
ports = test_endpoint("Local: /api/mycobrain/ports", f"{local_base}/api/mycobrain/ports")

print("\n[TEST 3] Checking Available Ports...")
print("-" * 80)
if ports and isinstance(ports, dict):
    port_list = ports.get('ports', [])
    print(f"  Found {len(port_list)} port(s):")
    for p in port_list:
        port_name = p.get('port') or p.get('device', 'unknown')
        print(f"    - {port_name}")

print("\n[TEST 4] Testing Device Connection (if COM7 found)...")
print("-" * 80)

# Try to connect to COM7
if ports and any((p.get('port') or p.get('device', '')).upper() == 'COM7' for p in ports.get('ports', [])):
    print("  COM7 found, attempting connection...")
    result = test_endpoint("Connect to COM7", 
                          f"{local_base}/api/mycobrain", 
                          "POST", 
                          {"action": "connect", "port": "COM7"})
    time.sleep(2)
    
    # Check devices again
    devices = test_endpoint("Check devices after connect", f"{local_base}/api/mycobrain/devices")
else:
    print("  COM7 not found in available ports")

print("\n[TEST 5] Testing Device Controls (if device connected)...")
print("-" * 80)

if devices and isinstance(devices, dict):
    device_list = devices.get('devices', [])
    if device_list:
        port = device_list[0].get('port', 'COM7')
        print(f"  Using device on {port}")
        
        # Test LED
        test_endpoint("LED Control", 
                     f"{local_base}/api/mycobrain",
                     "POST",
                     {"action": "neopixel", "port": port, "data": {"r": 0, "g": 255, "b": 0, "brightness": 128, "mode": "solid"}})
        
        time.sleep(1)
        
        # Test Buzzer
        test_endpoint("Buzzer Control",
                     f"{local_base}/api/mycobrain",
                     "POST",
                     {"action": "buzzer", "port": port, "data": {"frequency": 1000, "duration_ms": 100, "pattern": "beep"}})
        
        time.sleep(1)
        
        # Test Sensors
        sensors = test_endpoint("Get Sensor Data",
                               f"{local_base}/api/mycobrain/{port}/sensors")
        
        if sensors:
            print("\n  Sensor Data:")
            sensor_data = sensors.get('sensors', {})
            for sensor_name, data in sensor_data.items():
                if isinstance(data, dict):
                    print(f"    {sensor_name}:")
                    for key, value in data.items():
                        print(f"      {key}: {value}")
    else:
        print("  No devices connected")

print("\n" + "=" * 80)
print("TESTING COMPLETE")
print("=" * 80)
