#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Force ESP32-S3 into boot mode and upload firmware
"""
import subprocess
import time
import serial
import sys

def reset_serial_port(port):
    """Try to reset the serial port by opening and closing it."""
    try:
        s = serial.Serial(port, 115200, timeout=0.1)
        s.setDTR(False)  # Pull DTR low
        s.setRTS(True)   # Pull RTS high
        time.sleep(0.1)
        s.setDTR(True)   # Pull DTR high
        s.setRTS(False)  # Pull RTS low
        time.sleep(0.1)
        s.close()
        return True
    except Exception as e:
        print(f"  Reset attempt failed: {e}")
        return False

def try_connect(port, baud=115200):
    """Try to connect to ESP32 in boot mode."""
    cmd = [
        "python", "-m", "esptool",
        "--port", port,
        "--baud", str(baud),
        "--before", "default-reset",
        "--after", "hard-reset",
        "chip-id"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("  ✓ Connected!")
            return True
        else:
            print("  ✗ Not in boot mode")
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def erase_flash(port, baud=115200):
    """Erase flash memory."""
    print("\n[3] Erasing flash...")
    cmd = [
        "python", "-m", "esptool",
        "--port", port,
        "--baud", str(baud),
        "--before", "default-reset",
        "--after", "hard-reset",
        "erase_flash"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("  ✓ Flash erased")
            return True
        else:
            print("  ✗ Erase failed")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def main():
    port = "COM4"
    
    print("="*60)
    print("ESP32-S3 Force Boot Mode & Upload")
    print("="*60)
    
    print("\n[1] Attempting automatic reset via serial port...")
    reset_serial_port(port)
    time.sleep(1)
    
    print("\n[2] Testing connection...")
    if try_connect(port, 115200):
        print("\n✓ Device is in boot mode! You can now upload from Arduino IDE.")
        print("\nOr continue to erase flash and prepare for upload...")
        response = input("\nErase flash? (y/n): ").strip().lower()
        if response == 'y':
            erase_flash(port)
        return True
    
    print("\n" + "="*60)
    print("DEVICE NOT IN BOOT MODE")
    print("="*60)
    print("\nManual boot mode required:")
    print("1. UNPLUG USB cable completely")
    print("2. Wait 10 seconds")
    print("3. HOLD BOOT button (keep holding)")
    print("4. PLUG USB cable back in (still holding BOOT)")
    print("5. HOLD BOOT for 5 seconds")
    print("6. RELEASE BOOT button")
    print("7. Wait 2 seconds")
    print("\nThen run this script again OR upload from Arduino IDE immediately")
    print("\nAlternative method:")
    print("1. Hold BOOT button")
    print("2. Press and release RESET button (while holding BOOT)")
    print("3. Keep holding BOOT for 3 seconds")
    print("4. Release BOOT")
    print("5. Upload immediately")
    
    return False

if __name__ == "__main__":
    main()

