#!/usr/bin/env python3
"""Test MycoBrain commands via API to verify device firmware support"""

import requests
import json
import time

BASE_URL = "http://localhost:8003"
DEVICE_ID = "mycobrain-side-a-COM4"

def test_command(cmd_name: str, parameters: dict = None):
    """Test a command and return the response"""
    url = f"{BASE_URL}/devices/{DEVICE_ID}/command"
    payload = {
        "command": {"cmd": cmd_name, **(parameters or {})},
        "use_mdp": False
    }
    
    print(f"\n{'='*60}")
    print(f"Testing command: {cmd_name}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print(f"{'='*60}")
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        result = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(result, indent=2)}")
        return result
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    print("MycoBrain Command Testing")
    print("=" * 60)
    print(f"Device ID: {DEVICE_ID}")
    print(f"Base URL: {BASE_URL}")
    
    # Test 1: Ping (simple connectivity test)
    test_command("ping")
    time.sleep(1)
    
    # Test 2: Status (device status)
    test_command("status")
    time.sleep(1)
    
    # Test 3: Get MAC address
    test_command("get_mac")
    time.sleep(1)
    
    # Test 4: Get version
    test_command("get_version")
    time.sleep(1)
    
    # Test 5: I2C scan (from MDP spec)
    test_command("i2c_scan")
    time.sleep(2)  # I2C scan may take longer
    
    # Test 6: Read sensor (from MDP spec)
    test_command("read_sensor", {"sensor_id": 0})
    time.sleep(1)
    
    # Test 7: Set telemetry interval (from MDP spec)
    test_command("set_telemetry_interval", {"interval_seconds": 10})
    time.sleep(1)
    
    # Test 8: Set MOSFET (from MDP spec)
    test_command("set_mosfet", {"mosfet_index": 0, "state": True})
    time.sleep(1)
    
    # Test 9: Try neopixel (might not be supported)
    test_command("neopixel", {"r": 255, "g": 0, "b": 0, "brightness": 128})
    time.sleep(1)
    
    # Test 10: Try buzzer (might not be supported)
    test_command("buzzer", {"frequency": 1000, "duration": 500})
    time.sleep(1)
    
    # Test 11: Try set_neopixel (alternative name)
    test_command("set_neopixel", {"r": 255, "g": 0, "b": 0, "brightness": 128})
    time.sleep(1)
    
    # Test 12: Try play_buzzer (alternative name)
    test_command("play_buzzer", {"frequency": 1000, "duration": 500})
    time.sleep(1)
    
    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)
    print("\nSummary:")
    print("- Commands from MDP spec: i2c_scan, read_sensor, set_telemetry_interval, set_mosfet")
    print("- Simple commands: ping, status, get_mac, get_version")
    print("- Peripheral commands: neopixel, buzzer (may not be supported)")

if __name__ == "__main__":
    main()

