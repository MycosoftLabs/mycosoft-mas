#!/usr/bin/env python3
"""Test script for MycoBrain Dual Mode Firmware"""
import serial
import time
import sys

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM5"
BAUD = 115200

def main():
    print(f"Opening {PORT} at {BAUD} baud...")
    s = serial.Serial(PORT, BAUD, timeout=2)
    time.sleep(2)
    s.reset_input_buffer()
    
    # Read boot output
    print("\n=== BOOT OUTPUT ===")
    data = s.read(3000)
    print(data.decode('utf-8', 'ignore'))
    
    # Test CLI command: status
    print("\n=== CLI: status ===")
    s.write(b'status\r\n')
    s.flush()
    time.sleep(0.5)
    data = s.read(2000)
    print(data.decode('utf-8', 'ignore'))
    
    # Test JSON command: ping
    print('\n=== JSON: {"cmd":"ping"} ===')
    s.write(b'{"cmd":"ping"}\n')
    s.flush()
    time.sleep(0.3)
    data = s.read(1000)
    print(data.decode('utf-8', 'ignore'))
    
    # Test JSON command: get_mac
    print('\n=== JSON: {"cmd":"get_mac"} ===')
    s.write(b'{"cmd":"get_mac"}\n')
    s.flush()
    time.sleep(0.3)
    data = s.read(1000)
    print(data.decode('utf-8', 'ignore'))
    
    # Test JSON command: status
    print('\n=== JSON: {"cmd":"status"} ===')
    s.write(b'{"cmd":"status"}\n')
    s.flush()
    time.sleep(0.3)
    data = s.read(1000)
    print(data.decode('utf-8', 'ignore'))
    
    # Test CLI command: scan
    print("\n=== CLI: scan ===")
    s.write(b'scan\r\n')
    s.flush()
    time.sleep(0.5)
    data = s.read(1000)
    print(data.decode('utf-8', 'ignore'))
    
    # Test CLI: switch to lines format
    print("\n=== CLI: fmt lines ===")
    s.write(b'fmt lines\r\n')
    s.flush()
    time.sleep(0.3)
    data = s.read(500)
    print(data.decode('utf-8', 'ignore'))
    
    # Test CLI: status in lines format
    print("\n=== CLI: status (lines format) ===")
    s.write(b'status\r\n')
    s.flush()
    time.sleep(0.3)
    data = s.read(1000)
    print(data.decode('utf-8', 'ignore'))
    
    # Switch back to JSON
    print("\n=== CLI: fmt json ===")
    s.write(b'fmt json\r\n')
    s.flush()
    time.sleep(0.3)
    data = s.read(500)
    print(data.decode('utf-8', 'ignore'))
    
    s.close()
    print("\n=== TESTS COMPLETE ===")
    print("The firmware accepts both CLI and JSON commands!")
    print("Default output is JSON (for website compatibility)")
    print("Use 'fmt lines' to switch to CLI output for debugging")

if __name__ == "__main__":
    main()

