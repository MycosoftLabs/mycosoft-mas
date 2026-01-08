#!/usr/bin/env python3
"""Direct serial test for MycoBrain device"""
import serial
import time
import sys

def test_port(port_name):
    print(f"Testing {port_name}...")
    try:
        ser = serial.Serial(port_name, 115200, timeout=3, write_timeout=3)
        print("  Port opened successfully")
        time.sleep(2)  # Wait for any boot sequence
        
        # Drain any boot messages
        boot_data = b''
        while ser.in_waiting:
            boot_data += ser.read(ser.in_waiting)
            time.sleep(0.1)
        
        if boot_data:
            decoded = boot_data.decode("utf-8", errors="ignore")
            print(f"  Boot messages:\n{decoded[:500]}")
        else:
            print("  No boot messages received")
        
        # Send newline to wake up
        print("  Sending wake-up...")
        ser.write(b'\r\n')
        time.sleep(0.5)
        
        # Send status command
        print("  Sending: status")
        ser.write(b'status\r\n')
        time.sleep(1)
        
        response = ser.read(ser.in_waiting) if ser.in_waiting else b''
        if response:
            decoded = response.decode("utf-8", errors="ignore")
            print(f"  Response:\n{decoded}")
            return True
        else:
            print("  NO RESPONSE - Device may need firmware reflash")
            
            # Try help command
            print("  Trying: help")
            ser.write(b'help\r\n')
            time.sleep(1)
            
            help_response = ser.read(ser.in_waiting) if ser.in_waiting else b''
            if help_response:
                print(f"  Help response:\n{help_response.decode('utf-8', errors='ignore')}")
                return True
            
            # Check for bootloader mode
            print("  Checking for bootloader...")
            ser.setDTR(False)
            time.sleep(0.1)
            ser.setDTR(True)
            time.sleep(0.5)
            
            bootloader_check = ser.read(ser.in_waiting) if ser.in_waiting else b''
            if bootloader_check:
                decoded = bootloader_check.decode("utf-8", errors="ignore").lower()
                print(f"  Bootloader check: {decoded[:200]}")
                if 'waiting' in decoded or 'download' in decoded or 'boot' in decoded:
                    print("  >>> DEVICE IS IN BOOTLOADER MODE <<<")
            else:
                print("  No bootloader response - device may be unresponsive")
            
            return False
        
        ser.close()
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else "COM5"
    test_port(port)
