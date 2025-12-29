#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check if device is in boot loop
"""
import serial
import time

port = "COM5"
baud = 115200

print("="*60)
print("Checking for Boot Loop")
print("="*60)
print(f"\nPort: {port}")
print(f"Baud: {baud}")
print("\nReading for 15 seconds...")
print("(Watch for repeating patterns = boot loop)")

try:
    s = serial.Serial(port, baud, timeout=1)
    print("OK: Port opened")
    
    time.sleep(2)
    s.reset_input_buffer()
    
    # Collect data for 15 seconds
    data = b''
    start_time = time.time()
    
    while time.time() - start_time < 15:
        chunk = s.read(1000)
        if chunk:
            data += chunk
            print(f"  Got {len(chunk)} bytes at {int(time.time() - start_time)}s")
        time.sleep(0.1)
    
    s.close()
    
    if data:
        output = data.decode('utf-8', errors='ignore')
        print(f"\n{'='*60}")
        print(f"TOTAL DATA: {len(data)} bytes")
        print(f"{'='*60}")
        print(output)
        print(f"{'='*60}")
        
        # Check for boot loop indicators
        if 'ESP-ROM' in output or 'rst:' in output.lower():
            print("\n*** BOOT LOOP DETECTED ***")
            print("Device is resetting continuously")
        elif 'MINIMAL TEST' in output:
            print("\n*** MINIMAL TEST FIRMWARE RUNNING ***")
            print("Hardware is OK!")
        elif 'SuperMorgIO' in output or 'MycoBrain' in output:
            print("\n*** MAIN FIRMWARE RUNNING ***")
            print("Device is working!")
        elif len(output.strip()) == 0:
            print("\n*** NO OUTPUT ***")
            print("Device may be:")
            print("  - In bootloader mode")
            print("  - Crashed silently")
            print("  - No firmware running")
        else:
            print("\n*** UNKNOWN STATE ***")
            print("Device is outputting something but unclear what")
    else:
        print("\n*** NO DATA RECEIVED ***")
        print("Device is not sending anything")
        print("Possible causes:")
        print("  - In bootloader mode (waiting for upload)")
        print("  - Firmware crashed and not running")
        print("  - Hardware issue")
        
except serial.SerialException as e:
    print(f"\nERROR: Cannot open {port}")
    print(f"  {e}")
except Exception as e:
    print(f"\nERROR: {e}")

