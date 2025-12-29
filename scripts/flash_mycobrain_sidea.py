#!/usr/bin/env python3
"""
Direct firmware upload for MycoBrain Side-A using esptool
"""
import subprocess
import sys
import os
import time

def run_esptool(cmd_args, description):
    """Run esptool command."""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    try:
        result = subprocess.run(
            ["python", "-m", "esptool"] + cmd_args,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print("✓ SUCCESS")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print("✗ FAILED")
            if result.stderr:
                print(result.stderr)
            if result.stdout:
                print(result.stdout)
            return False
    except subprocess.TimeoutExpired:
        print("✗ TIMEOUT")
        return False
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False

def main():
    port = "COM4"
    baud = "115200"
    
    print("\n" + "="*60)
    print("MycoBrain Side-A Direct Flash Tool")
    print("="*60)
    
    # Step 1: Check connection
    print("\n[1/4] Checking device connection...")
    if not run_esptool(["--port", port, "--baud", baud, "chip_id"], "Reading chip ID"):
        print("\n⚠ Device not responding. Trying to put in boot mode...")
        print("Please:")
        print("  1. Hold BOOT button on ESP32")
        print("  2. Press and release RESET button")
        print("  3. Release BOOT button")
        print("  4. Press Enter when ready...")
        input()
        
        if not run_esptool(["--port", port, "--baud", baud, "chip_id"], "Reading chip ID (retry)"):
            print("\n✗ Cannot connect to device. Check:")
            print("  - USB cable is data-capable")
            print("  - COM port is correct")
            print("  - Device is powered")
            return False
    
    # Step 2: Erase flash
    print("\n[2/4] Erasing flash...")
    run_esptool(["--port", port, "--baud", baud, "erase_flash"], "Erasing flash")
    
    # Step 3: Get firmware path
    firmware_dir = os.path.join(os.path.dirname(__file__), "..", "firmware", "MycoBrain_SideA")
    print(f"\n[3/4] Looking for compiled firmware in: {firmware_dir}")
    
    # Note: Arduino IDE compiles to temp folder, we need to find the .bin file
    # Or compile it first
    print("\n⚠ Note: Arduino IDE compiles to temp folder.")
    print("You need to:")
    print("  1. Compile in Arduino IDE first")
    print("  2. Find the .bin file location (shown during compile)")
    print("  3. Or use Arduino CLI to compile and get .bin file")
    
    return True

if __name__ == "__main__":
    main()

