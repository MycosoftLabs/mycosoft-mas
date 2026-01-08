#!/usr/bin/env python3
"""Test MycoBrain buzzer and lights - you should SEE lights and HEAR beeps!"""

import serial
import time
import requests

print("=" * 60)
print("MYCOBRAIN COMPLETE TEST - BUZZER & LIGHTS")
print("=" * 60)
print()

# Step 1: Direct Serial Tests
print("STEP 1: Direct Serial Commands")
print("-" * 60)

try:
    ser = serial.Serial('COM7', 115200, timeout=3)
    print("✅ Connected to COM7")
    time.sleep(2)
    
    # Clear buffer
    if ser.in_waiting:
        ser.read(ser.in_waiting)
    
    tests = [
        ("STATUS", b'status\n', False),
        ("LED RED (LOOK FOR RED LIGHT!)", b'led red\n', True),
        ("LED GREEN (LOOK FOR GREEN LIGHT!)", b'led green\n', True),
        ("LED BLUE (LOOK FOR BLUE LIGHT!)", b'led blue\n', True),
        ("BUZZER BEEP (LISTEN FOR BEEP!)", b'buzzer beep\n', True),
        ("BUZZER COIN (LISTEN FOR COIN SOUND!)", b'buzzer coin\n', True),
        ("I2C SCAN", b'scan\n', False),
        ("LED OFF", b'led off\n', True),
    ]
    
    for name, cmd, wait in tests:
        print(f"\n{name}...")
        ser.write(cmd)
        time.sleep(0.5 if wait else 0.3)
        if ser.in_waiting:
            response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore').strip()
            if 'ok' in response.lower() or 'status' in response.lower() or 'telemetry' in response.lower():
                print(f"  ✅ Success")
            else:
                print(f"  ⚠️  Response: {response[:80]}")
        if wait:
            time.sleep(1)  # Wait to see/hear the effect
    
    ser.close()
    print("\n✅ Direct serial tests complete!")
    
except Exception as e:
    print(f"❌ Serial error: {e}")
    import traceback
    traceback.print_exc()

print()
print("STEP 2: Service API Commands")
print("-" * 60)

try:
    base = 'http://localhost:8003'
    
    # Check service
    health = requests.get(f'{base}/health', timeout=2)
    if health.status_code == 200:
        print("✅ Service is running")
    else:
        print(f"❌ Service health check failed: {health.status_code}")
        exit(1)
    
    # Get or connect device
    devices_resp = requests.get(f'{base}/devices', timeout=2)
    devices = devices_resp.json()
    device_list = devices.get('devices', [])
    
    if not device_list:
        print("⚠️  No devices connected. Connecting COM7...")
        connect_resp = requests.post(f'{base}/devices/connect/COM7', timeout=10)
        if connect_resp.status_code == 200:
            print("✅ Connected to COM7")
            device_id = connect_resp.json().get('device_id')
        else:
            print(f"❌ Connection failed: {connect_resp.text}")
            exit(1)
    else:
        device_id = device_list[0]['device_id']
        print(f"✅ Found device: {device_id}")
    
    time.sleep(1)
    
    # Test commands via API
    api_tests = [
        ("set_neopixel RED (LOOK FOR RED!)", {'command_type': 'set_neopixel', 'r': 255, 'g': 0, 'b': 0}),
        ("set_neopixel GREEN (LOOK FOR GREEN!)", {'command_type': 'set_neopixel', 'r': 0, 'g': 255, 'b': 0}),
        ("set_neopixel BLUE (LOOK FOR BLUE!)", {'command_type': 'set_neopixel', 'r': 0, 'g': 0, 'b': 255}),
        ("set_buzzer 1000Hz (LISTEN FOR BEEP!)", {'command_type': 'set_buzzer', 'frequency': 1000, 'duration': 300}),
        ("set_buzzer 2000Hz (LISTEN FOR HIGH BEEP!)", {'command_type': 'set_buzzer', 'frequency': 2000, 'duration': 300}),
        ("i2c_scan", {'command_type': 'i2c_scan'}),
        ("set_neopixel OFF", {'command_type': 'set_neopixel', 'r': 0, 'g': 0, 'b': 0}),
    ]
    
    for name, cmd_data in api_tests:
        print(f"\n{name}...")
        try:
            resp = requests.post(f'{base}/devices/{device_id}/command', json={
                'command': cmd_data
            }, timeout=5)
            if resp.status_code == 200:
                result = resp.json()
                print(f"  ✅ Success: {result.get('status', 'sent')}")
            else:
                print(f"  ❌ Failed: {resp.status_code} - {resp.text[:100]}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        if 'buzzer' in name.lower() or 'neopixel' in name.lower():
            time.sleep(1)  # Wait to see/hear effect
        else:
            time.sleep(0.5)
    
    # Get telemetry
    print("\nGetting telemetry...")
    try:
        resp = requests.get(f'{base}/devices/{device_id}/telemetry', timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('status') == 'ok':
                print("  ✅ Telemetry received")
            else:
                print(f"  ⚠️  Telemetry: {data}")
    except Exception as e:
        print(f"  ❌ Telemetry error: {e}")
    
    print("\n✅ All API tests complete!")
    
except Exception as e:
    print(f"❌ API error: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("TEST COMPLETE!")
print("=" * 60)
print("If you saw lights change and heard beeps, everything is working!")
print("Now test via website: http://localhost:3000/natureos/devices")
print()
