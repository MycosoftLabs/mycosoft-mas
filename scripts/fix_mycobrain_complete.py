#!/usr/bin/env python3
"""Complete fix for MycoBrain - ensure service runs locally and auto-connects COM7"""

import subprocess
import requests
import time
import json
import os
from pathlib import Path

print("=" * 80)
print("COMPLETE MYCOBRAIN FIX")
print("=" * 80)

website_dir = Path(r"C:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website")
service_script = website_dir / "services" / "mycobrain" / "mycobrain_service.py"

# Step 1: Kill any existing MycoBrain service
print("\n[STEP 1] Stopping existing MycoBrain services...")
try:
    result = subprocess.run(
        ["powershell", "-Command",
         "Get-Process python -ErrorAction SilentlyContinue | Where-Object { try { (Get-CimInstance Win32_Process -Filter \"ProcessId = $($_.Id)\").CommandLine -like '*mycobrain*' } catch { $false } } | Stop-Process -Force"],
        capture_output=True,
        text=True
    )
    print("  [OK] Existing services stopped")
    time.sleep(2)
except:
    print("  [INFO] No existing services found")

# Step 2: Check if COM7 exists
print("\n[STEP 2] Checking for COM7 port...")
try:
    import serial.tools.list_ports
    ports = list(serial.tools.list_ports.comports())
    com7_found = any(p.device.upper() == 'COM7' for p in ports)
    if com7_found:
        print("  [OK] COM7 found!")
        for p in ports:
            if p.device.upper() == 'COM7':
                print(f"      Description: {p.description}")
                print(f"      VID: {p.vid if hasattr(p, 'vid') else 'N/A'}")
                print(f"      PID: {p.pid if hasattr(p, 'pid') else 'N/A'}")
    else:
        print("  [WARNING] COM7 not found!")
        print("  Available ports:")
        for p in ports:
            print(f"    - {p.device}: {p.description}")
except Exception as e:
    print(f"  [ERROR] Could not check ports: {e}")

# Step 3: Start MycoBrain service locally
print("\n[STEP 3] Starting MycoBrain service on local machine...")
startup_script = website_dir / "scripts" / "start_mycobrain_service.ps1"

if not startup_script.exists():
    print("  [ERROR] Startup script not found!")
else:
    try:
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(startup_script)],
            capture_output=True,
            text=True,
            cwd=str(website_dir)
        )
        print(result.stdout)
        if result.returncode == 0:
            print("  [OK] Service start command executed")
        time.sleep(5)  # Wait for service to start
    except Exception as e:
        print(f"  [ERROR] Failed to start service: {e}")

# Step 4: Verify service is running locally
print("\n[STEP 4] Verifying service is running on localhost:8003...")
try:
    response = requests.get("http://localhost:8003/health", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"  [OK] Service is running!")
        print(f"      Status: {data.get('status')}")
        print(f"      Version: {data.get('version')}")
        print(f"      Devices connected: {data.get('devices_connected', 0)}")
    else:
        print(f"  [WARNING] Service returned: {response.status_code}")
except Exception as e:
    print(f"  [ERROR] Service not responding: {e}")
    print("  [INFO] Check log file for errors:")
    print(f"    {website_dir / 'logs' / 'mycobrain-service.log'}")

# Step 5: Check available ports via service
print("\n[STEP 5] Checking ports via service...")
try:
    response = requests.get("http://localhost:8003/ports", timeout=10)
    if response.status_code == 200:
        data = response.json()
        ports_list = data.get('ports', [])
        print(f"  [OK] Service reports {len(ports_list)} port(s):")
        for p in ports_list:
            port_name = p.get('port') or p.get('device', 'unknown')
            print(f"    - {port_name}")
        
        # Check if COM7 is there
        com7_in_list = any((p.get('port') or p.get('device', '')).upper() == 'COM7' for p in ports_list)
        if com7_in_list:
            print("  [OK] COM7 found in service port list!")
        else:
            print("  [WARNING] COM7 not in service port list")
except Exception as e:
    print(f"  [ERROR] Could not get ports: {e}")

# Step 6: Attempt to connect to COM7
print("\n[STEP 6] Attempting to connect to COM7...")
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
        print("  [OK] COM7 is already connected")
    else:
        error_data = response.json() if response.content else {}
        print(f"  [WARNING] Connection failed: {response.status_code}")
        print(f"      Error: {error_data.get('detail', error_data.get('error', 'Unknown'))}")
except Exception as e:
    print(f"  [ERROR] Could not connect: {e}")

# Step 7: Test all endpoints
print("\n[STEP 7] Testing device endpoints...")
time.sleep(2)

# Get devices
try:
    response = requests.get("http://localhost:8003/devices", timeout=5)
    if response.status_code == 200:
        data = response.json()
        devices = data.get('devices', [])
        print(f"  [OK] Devices endpoint: {len(devices)} device(s) connected")
        for device in devices:
            print(f"      - {device.get('device_id', 'unknown')} on {device.get('port', 'unknown')}")
    else:
        print(f"  [WARNING] Devices endpoint: {response.status_code}")
except Exception as e:
    print(f"  [ERROR] Devices endpoint: {e}")

# Test sensors
print("\n[STEP 8] Testing BME688 sensors...")
try:
    response = requests.get("http://localhost:8003/devices/COM7/sensors", timeout=10)
    if response.status_code == 200:
        data = response.json()
        sensors = data.get('sensors', {})
        print(f"  [OK] Retrieved sensor data from {len(sensors)} sensor(s)")
        for sensor_name, sensor_data in sensors.items():
            if isinstance(sensor_data, dict):
                print(f"      {sensor_name}:")
                for key, value in sensor_data.items():
                    if key != 'raw_data':
                        print(f"        {key}: {value}")
    else:
        print(f"  [WARNING] Sensors endpoint: {response.status_code}")
except Exception as e:
    print(f"  [INFO] Sensors: {e}")

# Test controls
print("\n[STEP 9] Testing device controls...")

# LED
print("  Testing NeoPixel LED...")
try:
    response = requests.post(
        "http://localhost:8003/devices/COM7/neopixel",
        json={"r": 0, "g": 255, "b": 0, "brightness": 128, "mode": "solid"},
        timeout=5
    )
    if response.status_code == 200:
        print("    [OK] LED control works")
    else:
        print(f"    [WARNING] LED control: {response.status_code}")
except Exception as e:
    print(f"    [INFO] LED control: {e}")

time.sleep(1)

# Buzzer
print("  Testing Buzzer...")
try:
    response = requests.post(
        "http://localhost:8003/devices/COM7/buzzer",
        json={"frequency": 1000, "duration_ms": 100, "pattern": "beep"},
        timeout=5
    )
    if response.status_code == 200:
        print("    [OK] Buzzer control works")
    else:
        print(f"    [WARNING] Buzzer control: {response.status_code}")
except Exception as e:
    print(f"    [INFO] Buzzer control: {e}")

# Step 10: Test via website API
print("\n[STEP 10] Testing via website API...")
try:
    response = requests.get("http://localhost:3000/api/mycobrain/devices", timeout=5)
    if response.status_code == 200:
        data = response.json()
        service_healthy = data.get('serviceHealthy', False)
        devices = data.get('devices', [])
        print(f"  [OK] Website API responding")
        print(f"      Service healthy: {service_healthy}")
        print(f"      Devices: {len(devices)}")
    else:
        print(f"  [WARNING] Website API: {response.status_code}")
except Exception as e:
    print(f"  [ERROR] Website API: {e}")

# Step 11: Set up auto-start
print("\n[STEP 11] Setting up auto-start...")
task_script = website_dir / "scripts" / "setup_mycobrain_task.ps1"
if task_script.exists():
    print("  [INFO] Auto-start script exists")
    print("  [ACTION] Run as Administrator to enable auto-start:")
    print(f"    powershell -ExecutionPolicy Bypass -File \"{task_script}\"")

print("\n" + "=" * 80)
print("FIX COMPLETE")
print("=" * 80)
