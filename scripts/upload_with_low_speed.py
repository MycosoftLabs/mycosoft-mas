#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Upload firmware with very low speed and multiple retry attempts
"""
import subprocess
import time
import sys

def upload_with_speed(port, baud, description):
    """Try upload with specific baud rate."""
    print(f"\nTrying {description} (baud: {baud})...")
    
    # First, try to connect
    cmd_connect = [
        "python", "-m", "esptool",
        "--port", port,
        "--baud", str(baud),
        "--before", "default-reset",
        "--after", "hard-reset",
        "chip-id"
    ]
    
    try:
        result = subprocess.run(cmd_connect, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            print(f"  ✓ Connected at {baud} baud!")
            print(f"\n  Now try uploading from Arduino IDE with:")
            print(f"  - Upload Speed: {baud}")
            print(f"  - Port: {port}")
            return True
        else:
            print(f"  ✗ Failed at {baud} baud")
            return False
    except subprocess.TimeoutExpired:
        print(f"  ✗ Timeout at {baud} baud")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def main():
    port = "COM4"
    
    print("="*60)
    print("ESP32-S3 Low-Speed Upload Test")
    print("="*60)
    
    print("\nThis will test different upload speeds.")
    print("Put device in boot mode first:")
    print("  1. Unplug USB")
    print("  2. Hold BOOT")
    print("  3. Plug USB in (keep holding BOOT)")
    print("  4. Hold BOOT 5 seconds, release")
    print("  5. Press Enter when ready...")
    input()
    
    speeds = [
        (115200, "Standard"),
        (9600, "Very Slow (most reliable)"),
        (460800, "Fast"),
        (230400, "Medium"),
    ]
    
    for baud, desc in speeds:
        if upload_with_speed(port, baud, desc):
            print(f"\n✓ Use {baud} baud in Arduino IDE!")
            return True
        time.sleep(1)
    
    print("\n✗ Could not connect at any speed.")
    print("Device may not be in boot mode or hardware issue.")
    return False

if __name__ == "__main__":
    main()

