#!/usr/bin/env python3
"""
Test MycoBrain Side-A Dual Mode Firmware
Tests both CLI and JSON command formats
"""

import serial
import time
import json
import sys

def test_mycobrain(port="COM5", baud=115200, timeout=2):
    """Test MycoBrain board with various commands"""
    
    print(f"\n{'='*60}")
    print(f"MycoBrain Side-A Command Test")
    print(f"{'='*60}")
    print(f"Port: {port}")
    print(f"Baud: {baud}")
    print()
    
    try:
        ser = serial.Serial(port, baud, timeout=timeout)
        time.sleep(1)  # Wait for connection
        
        # Clear any initial output
        ser.reset_input_buffer()
        
        # Test 1: CLI command - status
        print("Test 1: CLI command 'status'")
        print("-" * 60)
        ser.write(b"status\n")
        time.sleep(0.5)
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(response)
        print()
        
        # Test 2: JSON command - status
        print("Test 2: JSON command {'cmd':'status'}")
        print("-" * 60)
        cmd = {"cmd": "status"}
        ser.write((json.dumps(cmd) + "\n").encode())
        time.sleep(0.5)
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(response)
        print()
        
        # Test 3: Workbook-style JSON command
        print("Test 3: Workbook-style JSON {'type':'cmd','op':'status'}")
        print("-" * 60)
        cmd = {"type": "cmd", "op": "status"}
        ser.write((json.dumps(cmd) + "\n").encode())
        time.sleep(0.5)
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(response)
        print()
        
        # Test 4: CLI command - help
        print("Test 4: CLI command 'help'")
        print("-" * 60)
        ser.write(b"help\n")
        time.sleep(0.5)
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(response)
        print()
        
        # Test 5: JSON command - info
        print("Test 5: JSON command {'cmd':'info'}")
        print("-" * 60)
        cmd = {"cmd": "info"}
        ser.write((json.dumps(cmd) + "\n").encode())
        time.sleep(0.5)
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print(response)
        print()
        
        # Test 6: Wait for telemetry (should auto-send)
        print("Test 6: Waiting for auto-telemetry (5 seconds)...")
        print("-" * 60)
        start_time = time.time()
        while time.time() - start_time < 5:
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                print(response, end='')
            time.sleep(0.1)
        print()
        print()
        
        ser.close()
        print(f"{'='*60}")
        print("Test completed successfully!")
        print(f"{'='*60}")
        return True
        
    except serial.SerialException as e:
        print(f"ERROR: Serial communication failed: {e}")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else "COM5"
    success = test_mycobrain(port)
    sys.exit(0 if success else 1)
