#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple test to check if ESP32-S3 is in boot mode
"""
import subprocess
import sys

port = "COM4"

print("="*60)
print("ESP32-S3 Boot Mode Test")
print("="*60)
print(f"\nTesting {port}...")
print("\nMake sure device is in boot mode:")
print("  1. Unplug USB")
print("  2. Hold BOOT button")
print("  3. Plug USB in (keep holding BOOT)")
print("  4. Hold BOOT 5 seconds, release")
print("  5. Wait 2 seconds")
print("\nPress Enter when ready...")
input()

print("\nTesting connection...")
cmd = [
    "python", "-m", "esptool",
    "--port", port,
    "--baud", "115200",
    "chip-id"
]

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if result.returncode == 0:
        print("\nSUCCESS! Device is in boot mode.")
        print("You can now upload from Arduino IDE.")
        if "ESP32-S3" in result.stdout:
            print("Device confirmed: ESP32-S3")
    else:
        print("\nFAILED: Device not in boot mode.")
        print("\nOutput:")
        print(result.stderr)
        print("\nTry again with the boot mode procedure.")
except Exception as e:
    print(f"\nERROR: {e}")
    print("\nDevice is not responding. Check:")
    print("  - USB cable is data-capable")
    print("  - COM port is correct")
    print("  - Device is powered")
    print("  - Boot mode procedure was followed exactly")

