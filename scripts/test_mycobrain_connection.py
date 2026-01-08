#!/usr/bin/env python3
"""
MycoBrain Connection Test Script
Tests device connection and basic functionality
"""

import serial
import time
import sys

def test_port(port, baud=115200):
    """Test a serial port connection"""
    print(f"\n{'='*60}")
    print(f"Testing {port} at {baud} baud")
    print(f"{'='*60}")
    
    try:
        # Open connection
        ser = serial.Serial(port, baud, timeout=2)
        print(f"[OK] Connected to {port}")
        time.sleep(1)  # Wait for device to initialize
        
        # Clear any existing data
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Test 1: Send status command
        print("\n[TEST 1] Sending 'status' command...")
        ser.write(b'status\n')
        time.sleep(0.5)
        response = ser.read_all().decode('utf-8', errors='ignore')
        if response:
            print(f"[OK] Response: {response.strip()}")
        else:
            print("[WARN] No response")
        
        # Test 2: Machine mode initialization
        print("\n[TEST 2] Initializing machine mode...")
        commands = [
            ('mode machine', b'mode machine\n'),
            ('dbg off', b'dbg off\n'),
            ('fmt json', b'fmt json\n'),
            ('scan', b'scan\n'),
            ('status', b'status\n')
        ]
        
        for name, cmd in commands:
            print(f"  Sending: {name}")
            ser.write(cmd)
            time.sleep(0.5)
            response = ser.read_all().decode('utf-8', errors='ignore')
            if response:
                print(f"    [OK] Response: {response.strip()[:100]}")
            else:
                print(f"    [WARN] No response")
        
        # Test 3: Check for telemetry
        print("\n[TEST 3] Waiting for telemetry (5 seconds)...")
        start_time = time.time()
        while time.time() - start_time < 5:
            if ser.in_waiting > 0:
                data = ser.read_all().decode('utf-8', errors='ignore')
                if data:
                    print(f"  Received: {data.strip()[:100]}")
            time.sleep(0.1)
        
        ser.close()
        print(f"\n[OK] Test complete for {port}")
        return True
        
    except serial.SerialException as e:
        print(f"[ERROR] Serial error: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

def main():
    """Main test function"""
    print("="*60)
    print("MycoBrain Connection Test")
    print("="*60)
    
    # Test available ports
    ports_to_test = ['COM3', 'COM6']
    
    results = {}
    for port in ports_to_test:
        try:
            results[port] = test_port(port)
        except Exception as e:
            print(f"✗ Failed to test {port}: {e}")
            results[port] = False
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for port, success in results.items():
        status = "[OK] WORKING" if success else "[FAIL] FAILED"
        print(f"{port}: {status}")
    
    if any(results.values()):
        print("\n[OK] At least one port is working!")
        working_port = [p for p, s in results.items() if s][0]
        print(f"  Use {working_port} for device connection")
    else:
        print("\n[FAIL] No working ports found")
        print("  Check:")
        print("    - Device is powered on")
        print("    - USB cable is connected")
        print("    - Firmware is flashed correctly")
        print("    - No other program is using the COM port")

if __name__ == "__main__":
    main()
