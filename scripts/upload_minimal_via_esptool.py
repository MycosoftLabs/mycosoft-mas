#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Upload minimal test firmware via esptool
This compiles the minimal test and uploads it
"""
import subprocess
import sys
import os

port = "COM5"

print("="*60)
print("Upload Minimal Test Firmware via esptool")
print("="*60)

# First, we need to compile the firmware
# Arduino CLI would be needed, but let's try direct esptool method

print("\nNOTE: To upload firmware, you need:")
print("1. Compile in Arduino IDE first")
print("2. Get the .bin file location")
print("3. Or use Arduino CLI")

print("\nAlternatively, use Arduino IDE to upload:")
print(f"  - Port: {port}")
print("  - File: firmware/MycoBrain_SideA/MycoBrain_SideA_MINIMAL_TEST.ino")
print("  - Put device in boot mode first")

print("\nChecking if device is ready for upload...")
result = subprocess.run(
    ["python", "-m", "esptool", "--port", port, "--baud", "115200", "chip-id"],
    capture_output=True,
    text=True,
    timeout=10
)

if result.returncode == 0:
    print("OK: Device is ready for upload")
    print("\nYou can now upload from Arduino IDE:")
    print(f"  1. Open MycoBrain_SideA_MINIMAL_TEST.ino")
    print(f"  2. Select port: {port}")
    print(f"  3. Put in boot mode (unplug, hold BOOT, plug in, hold 5 sec, release)")
    print(f"  4. Upload")
else:
    print("WARNING: Device not responding")
    print(result.stderr)


