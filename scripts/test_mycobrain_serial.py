#!/usr/bin/env python3
"""Test MycoBrain serial communication directly"""

import serial
import time
import json

PORT = "COM4"
BAUDRATE = 115200

def test_serial():
    try:
        print(f"Connecting to {PORT} at {BAUDRATE} baud...")
        ser = serial.Serial(PORT, BAUDRATE, timeout=2)
        time.sleep(0.5)  # Wait for connection
        
        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Test 1: Simple ping
        print("\n[Test 1] Sending ping command...")
        ser.write(b'{"cmd": "ping"}\n')
        ser.flush()
        time.sleep(0.5)
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
            print(f"Response: {response}")
        else:
            print("No response")
        
        # Test 2: Status command
        print("\n[Test 2] Sending status command...")
        ser.reset_input_buffer()
        ser.write(b'{"cmd": "status"}\n')
        ser.flush()
        time.sleep(0.5)
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
            print(f"Response: {response}")
        else:
            print("No response")
        
        # Test 3: I2C scan
        print("\n[Test 3] Sending I2C scan command...")
        ser.reset_input_buffer()
        ser.write(b'{"cmd": "i2c_scan"}\n')
        ser.flush()
        time.sleep(1.0)  # I2C scan may take longer
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
            print(f"Response: {response}")
        else:
            print("No response")
        
        # Test 4: NeoPixel command
        print("\n[Test 4] Sending NeoPixel command...")
        ser.reset_input_buffer()
        cmd = json.dumps({"cmd": "neopixel", "r": 255, "g": 0, "b": 0, "brightness": 128})
        ser.write((cmd + "\n").encode('utf-8'))
        ser.flush()
        time.sleep(0.5)
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
            print(f"Response: {response}")
        else:
            print("No response")
        
        ser.close()
        print("\n✅ Serial test completed")
        
    except serial.SerialException as e:
        print(f"❌ Serial error: {e}")
        print("Make sure:")
        print("  1. Device is connected to COM4")
        print("  2. No other application is using the port")
        print("  3. Device is powered on")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_serial()

