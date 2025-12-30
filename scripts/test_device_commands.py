#!/usr/bin/env python3
"""
Test MycoBrain device commands via service API
"""

import requests
import json
import time

SERVICE_URL = "http://localhost:8003"
DEVICE_ID = None

def get_devices():
    """Get list of connected devices"""
    r = requests.get(f"{SERVICE_URL}/devices")
    return r.json()

def connect_device(port="COM5"):
    """Connect to device"""
    r = requests.post(
        f"{SERVICE_URL}/devices/connect/{port}",
        json={"port": port, "side": "side-a", "baudrate": 115200}
    )
    return r.json()

def send_command(device_id, command, parameters=None, use_mdp=False):
    """Send command to device"""
    payload = {
        "command": {
            "command_type": command,
            **(parameters or {})
        },
        "use_mdp": use_mdp
    }
    r = requests.post(
        f"{SERVICE_URL}/devices/{device_id}/command",
        json=payload
    )
    return r.json()

def get_telemetry(device_id):
    """Get device telemetry"""
    r = requests.get(f"{SERVICE_URL}/devices/{device_id}/telemetry")
    return r.json()

if __name__ == "__main__":
    print("=" * 60)
    print("MycoBrain Device Command Test")
    print("=" * 60)
    
    # Connect device
    print("\n1. Connecting to COM5...")
    result = connect_device("COM5")
    if "device_id" in result:
        DEVICE_ID = result["device_id"]
        print(f"   Connected: {DEVICE_ID}")
        print(f"   MAC: {result.get('mac_address', 'unknown')}")
    else:
        print(f"   Error: {result}")
        exit(1)
    
    time.sleep(1)
    
    # Test status
    print("\n2. Testing 'status' command...")
    result = send_command(DEVICE_ID, "status")
    print(f"   Response: {json.dumps(result, indent=2)}")
    
    time.sleep(0.5)
    
    # Test buzzer
    print("\n3. Testing 'set_buzzer' command...")
    result = send_command(DEVICE_ID, "set_buzzer", {"frequency": 1000, "duration": 200})
    print(f"   Response: {json.dumps(result, indent=2)}")
    
    time.sleep(0.5)
    
    # Test LED
    print("\n4. Testing 'set_neopixel' command...")
    result = send_command(DEVICE_ID, "set_neopixel", {"led_index": 0, "r": 255, "g": 0, "b": 255})
    print(f"   Response: {json.dumps(result, indent=2)}")
    
    time.sleep(0.5)
    
    # Test I2C scan
    print("\n5. Testing 'i2c_scan' command...")
    result = send_command(DEVICE_ID, "i2c_scan")
    print(f"   Response: {json.dumps(result, indent=2)}")
    
    time.sleep(1)
    
    # Get telemetry
    print("\n6. Getting telemetry...")
    result = get_telemetry(DEVICE_ID)
    print(f"   Telemetry: {json.dumps(result, indent=2)}")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

