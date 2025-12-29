#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Upload firmware to both MycoBrain boards
"""
import subprocess
import sys
import time

def upload_firmware(port, sketch_path):
    """Upload firmware to a board."""
    print(f"\n{'='*60}")
    print(f"Uploading to {port}")
    print(f"{'='*60}")
    
    # Compile first
    print("Compiling...")
    compile_cmd = [
        "arduino-cli", "compile",
        "--fqbn", "esp32:esp32:esp32s3",
        sketch_path
    ]
    
    result = subprocess.run(compile_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Compilation failed!")
        print(result.stderr)
        return False
    
    print("Compilation successful!")
    
    # Upload
    print(f"Uploading to {port}...")
    upload_cmd = [
        "arduino-cli", "upload",
        "-p", port,
        "--fqbn", "esp32:esp32:esp32s3",
        sketch_path
    ]
    
    result = subprocess.run(upload_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Upload failed!")
        print(result.stderr)
        return False
    
    print(f"Upload successful to {port}!")
    return True

def main():
    sketch = "firmware/MycoBrain_SideA/MycoBrain_SideA_FIXED.ino"
    ports = ["COM5", "COM7"]
    
    print("="*60)
    print("Uploading Firmware to Both Boards")
    print("="*60)
    
    for port in ports:
        if upload_firmware(port, sketch):
            print(f"\n✓ {port} done")
            time.sleep(2)
        else:
            print(f"\n✗ {port} failed")
    
    print("\n" + "="*60)
    print("Upload Complete")
    print("="*60)
    print("\nTesting boards in 5 seconds...")
    time.sleep(5)

if __name__ == "__main__":
    main()

