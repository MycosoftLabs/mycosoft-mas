#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Direct MycoBrain Side-A flash tool
"""
import subprocess
import sys
import time

def run_cmd(cmd, description):
    print(f"\n{description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print("SUCCESS")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print("FAILED")
            if result.stderr:
                print(result.stderr)
            return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    port = "COM4"
    
    print("="*60)
    print("MycoBrain Side-A Direct Flash")
    print("="*60)
    
    print("\nIMPORTANT: Put device in boot mode first!")
    print("1. Unplug USB")
    print("2. Hold BOOT button")
    print("3. Plug USB back in (keep holding BOOT)")
    print("4. Hold BOOT for 3 seconds")
    print("5. Release BOOT")
    print("\nPress Enter when device is in boot mode...")
    input()
    
    # Try to connect
    print("\n[1] Testing connection...")
    cmd = f'python -m esptool --port {port} --baud 115200 chip-id'
    if not run_cmd(cmd, "Connecting to device"):
        print("\nDevice not in boot mode. Trying automatic reset...")
        cmd = f'python -m esptool --port {port} --baud 115200 --before default-reset --after hard-reset chip-id'
        if not run_cmd(cmd, "Connecting with auto-reset"):
            print("\nFAILED: Cannot connect to device.")
            print("Make sure:")
            print("  - Device is in boot mode (BOOT button held)")
            print("  - USB cable is data-capable")
            print("  - COM port is correct")
            return False
    
    print("\n[2] Device connected! Reading info...")
    run_cmd(f'python -m esptool --port {port} --baud 115200 read-mac', "Reading MAC")
    run_cmd(f'python -m esptool --port {port} --baud 115200 flash-id', "Reading Flash ID")
    
    print("\n[3] Device is ready for upload!")
    print("Use Arduino IDE to upload firmware now.")
    print("Device should be in boot mode and ready.")
    
    return True

if __name__ == "__main__":
    main()


