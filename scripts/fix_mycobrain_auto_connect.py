#!/usr/bin/env python3
"""Fix MycoBrain service to auto-connect to COM7 and ensure it stays running"""

import subprocess
import requests
import time
import json

print("=" * 80)
print("FIXING MYCOBRAIN AUTO-CONNECT TO COM7")
print("=" * 80)

# Test if service is running
print("\n[STEP 1] Checking service status...")
try:
    response = requests.get("http://localhost:8003/health", timeout=5)
    if response.status_code == 200:
        print("  [OK] Service is running")
        data = response.json()
        print(f"      Devices connected: {data.get('devices_connected', 0)}")
    else:
        print(f"  [WARNING] Service returned: {response.status_code}")
except Exception as e:
    print(f"  [ERROR] Service not responding: {e}")
    print("  [ACTION] Starting service...")
    # Start service
    subprocess.Popen(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File",
         r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\scripts\start_mycobrain_service.ps1"],
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    print("  [INFO] Service start command issued, waiting 5 seconds...")
    time.sleep(5)

# Check available ports
print("\n[STEP 2] Checking available serial ports...")
try:
    response = requests.get("http://localhost:8003/ports", timeout=10)
    if response.status_code == 200:
        data = response.json()
        ports = data.get('ports', [])
        print(f"  [OK] Found {len(ports)} port(s):")
        for port in ports:
            port_name = port.get('port') or port.get('device', 'unknown')
            print(f"      - {port_name}")
        
        # Check if COM7 is available
        com7_found = any((p.get('port') or p.get('device', '')).upper() == 'COM7' for p in ports)
        if com7_found:
            print("  [OK] COM7 is available!")
        else:
            print("  [WARNING] COM7 not found in available ports")
    else:
        print(f"  [ERROR] Failed to get ports: {response.status_code}")
except Exception as e:
    print(f"  [ERROR] Could not check ports: {e}")

# Try to connect to COM7
print("\n[STEP 3] Attempting to connect to COM7...")
try:
    response = requests.post(
        "http://localhost:8003/devices/connect/COM7",
        json={"port": "COM7", "baudrate": 115200},
        timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        print("  [OK] Successfully connected to COM7!")
        print(f"      Device ID: {data.get('device_id', 'unknown')}")
        print(f"      Status: {data.get('status', 'unknown')}")
    elif response.status_code == 409:
        print("  [INFO] COM7 is already connected")
    else:
        print(f"  [WARNING] Connection failed: {response.status_code}")
        try:
            error_data = response.json()
            print(f"      Error: {error_data.get('detail', error_data.get('error', 'Unknown'))}")
        except:
            print(f"      Response: {response.text[:100]}")
except Exception as e:
    print(f"  [ERROR] Could not connect: {e}")

# Check connected devices
print("\n[STEP 4] Checking connected devices...")
try:
    response = requests.get("http://localhost:8003/devices", timeout=5)
    if response.status_code == 200:
        data = response.json()
        devices = data.get('devices', [])
        print(f"  [OK] {len(devices)} device(s) connected:")
        for device in devices:
            device_id = device.get('device_id', 'unknown')
            port = device.get('port', 'unknown')
            status = device.get('status', 'unknown')
            print(f"      - {device_id} on {port} ({status})")
except Exception as e:
    print(f"  [ERROR] Could not get devices: {e}")

# Test sensor data
print("\n[STEP 5] Testing sensor data retrieval...")
try:
    response = requests.get("http://localhost:8003/devices/COM7/sensors", timeout=10)
    if response.status_code == 200:
        data = response.json()
        print("  [OK] Sensor data retrieved:")
        sensors = data.get('sensors', {})
        for sensor_name, sensor_data in sensors.items():
            if isinstance(sensor_data, dict):
                temp = sensor_data.get('temperature', 'N/A')
                hum = sensor_data.get('humidity', 'N/A')
                print(f"      {sensor_name}: Temp={temp}°C, Humidity={hum}%")
    else:
        print(f"  [WARNING] Could not get sensor data: {response.status_code}")
except Exception as e:
    print(f"  [INFO] Sensor data not available: {e}")

# Test controls
print("\n[STEP 6] Testing device controls...")
print("  Testing LED control...")
try:
    response = requests.post(
        "http://localhost:8003/devices/COM7/neopixel",
        json={"r": 0, "g": 255, "b": 0, "brightness": 128, "mode": "solid"},
        timeout=5
    )
    if response.status_code == 200:
        print("  [OK] LED control works")
    else:
        print(f"  [WARNING] LED control failed: {response.status_code}")
except Exception as e:
    print(f"  [INFO] LED control: {e}")

print("\n  Testing buzzer control...")
try:
    response = requests.post(
        "http://localhost:8003/devices/COM7/buzzer",
        json={"frequency": 1000, "duration_ms": 100, "pattern": "beep"},
        timeout=5
    )
    if response.status_code == 200:
        print("  [OK] Buzzer control works")
    else:
        print(f"  [WARNING] Buzzer control failed: {response.status_code}")
except Exception as e:
    print(f"  [INFO] Buzzer control: {e}")

# Test via website API
print("\n[STEP 7] Testing via website API (localhost:3000)...")
try:
    response = requests.get("http://localhost:3000/api/mycobrain/devices", timeout=5)
    if response.status_code == 200:
        data = response.json()
        devices = data.get('devices', [])
        service_status = data.get('serviceHealthy', False)
        print(f"  [OK] Website API responding")
        print(f"      Service healthy: {service_status}")
        print(f"      Devices: {len(devices)}")
    else:
        print(f"  [WARNING] Website API returned: {response.status_code}")
except Exception as e:
    print(f"  [ERROR] Website API not responding: {e}")

print("\n" + "=" * 80)
print("TESTING COMPLETE")
print("=" * 80)
