#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor board for boot loop
"""
import serial
import time

port = "COM7"
print(f"Monitoring {port} for 20 seconds...")
print("Watch for repeating patterns = boot loop")

s = serial.Serial(port, 115200, timeout=1)
time.sleep(2)
s.reset_input_buffer()

data = b''
start = time.time()
while time.time() - start < 20:
    chunk = s.read(1000)
    if chunk:
        data += chunk
        print(f"[{int(time.time()-start)}s] {len(chunk)} bytes")
    time.sleep(0.1)

s.close()

if data:
    output = data.decode('utf-8', errors='ignore')
    print(f"\nTOTAL: {len(data)} bytes")
    print("="*60)
    print(output)
    print("="*60)
    
    # Check for boot loop
    if output.count("ESP-ROM") > 3:
        print("\n*** BOOT LOOP DETECTED - Device resetting repeatedly ***")
    elif "MINIMAL TEST" in output:
        print("\n*** FIRMWARE RUNNING - Device is working! ***")
else:
    print("\nNo data received")

