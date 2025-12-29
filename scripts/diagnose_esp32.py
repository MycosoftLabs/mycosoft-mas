#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESP32-S3 Diagnostic Tool
"""
import serial.tools.list_ports
import serial
import time
import sys

def check_ports():
    print("="*60)
    print("Available COM Ports:")
    print("="*60)
    ports = serial.tools.list_ports.comports()
    for p in ports:
        print(f"  {p.device:6} - {p.description}")
        if p.hwid:
            print(f"           HWID: {p.hwid}")
    print()

def test_serial_read(port, baud=115200):
    print(f"Testing {port} at {baud} baud...")
    try:
        s = serial.Serial(port, baud, timeout=2)
        time.sleep(0.5)
        s.reset_input_buffer()
        
        # Send reset command
        s.write(b'\r\n\r\n')
        time.sleep(1)
        
        # Try to read
        data = s.read(1000)
        if data:
            print(f"  Received: {data.decode('utf-8', errors='ignore')[:200]}")
            return True
        else:
            print("  No data received")
            return False
    except serial.SerialException as e:
        print(f"  Error: {e}")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False
    finally:
        try:
            s.close()
        except:
            pass

def main():
    print("\n" + "="*60)
    print("ESP32-S3 Diagnostic Tool")
    print("="*60)
    
    check_ports()
    
    port = "COM4"
    print(f"\nTesting {port}...")
    
    # Test different baud rates
    for baud in [115200, 9600, 230400]:
        print(f"\nTrying {baud} baud...")
        if test_serial_read(port, baud):
            print(f"  SUCCESS at {baud} baud!")
            break
    else:
        print("\n" + "="*60)
        print("DIAGNOSIS:")
        print("="*60)
        print("Device is not responding to serial communication.")
        print("\nPossible causes:")
        print("  1. Device is in bad state (needs boot mode)")
        print("  2. Firmware crashed and not running")
        print("  3. Hardware issue")
        print("  4. USB cable/port issue")
        print("\nSOLUTION:")
        print("  1. Unplug USB cable")
        print("  2. Wait 10 seconds")
        print("  3. Hold BOOT button")
        print("  4. Plug USB back in (keep holding BOOT)")
        print("  5. Hold BOOT for 5 seconds")
        print("  6. Release BOOT")
        print("  7. Try Arduino IDE upload immediately")
        print("\nOr try different USB cable/port")

if __name__ == "__main__":
    main()

