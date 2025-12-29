#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Direct test of Side-A device
"""
import serial
import serial.tools.list_ports
import time
import sys

def find_esp32_port():
    """Find ESP32-S3 COM port."""
    ports = serial.tools.list_ports.comports()
    for p in ports:
        # ESP32-S3 typically shows as VID:PID=303A:1001
        if '303A' in p.hwid or 'ESP' in p.description.upper():
            return p.device
    return None

def test_port(port, baud=115200):
    """Test communication with device."""
    print(f"\n{'='*60}")
    print(f"Testing {port} at {baud} baud")
    print(f"{'='*60}")
    
    try:
        s = serial.Serial(port, baud, timeout=2)
        print(f"✓ Port opened: {port}")
        
        # Wait a bit
        time.sleep(2)
        
        # Clear buffers
        s.reset_input_buffer()
        s.reset_output_buffer()
        
        # Send reset command
        print("\nSending reset command...")
        s.write(b'\r\n\r\n')
        time.sleep(1)
        
        # Try to read
        print("Reading data...")
        data = s.read(2000)
        
        if data:
            output = data.decode('utf-8', errors='ignore')
            print(f"\n{'='*60}")
            print("RECEIVED DATA:")
            print(f"{'='*60}")
            print(output)
            print(f"{'='*60}")
            
            # Check for boot loop
            if 'ESP-ROM' in output or 'rst:' in output.lower():
                print("\nWARNING: BOOT LOOP DETECTED - Device is resetting")
            elif 'MINIMAL TEST' in output or 'Hardware Check' in output:
                print("\nSUCCESS: MINIMAL TEST FIRMWARE RUNNING - Hardware is OK!")
            elif 'SuperMorgIO' in output or 'MycoBrain' in output:
                print("\nSUCCESS: MAIN FIRMWARE RUNNING - Device is working!")
            else:
                print("\nWARNING: Unknown output - Device may be in bootloader mode")
        else:
            print("\n✗ No data received")
            print("Device may be:")
            print("  - In bootloader mode (waiting for upload)")
            print("  - Crashed and resetting")
            print("  - No firmware running")
        
        s.close()
        return True
        
    except serial.SerialException as e:
        print(f"\n✗ Cannot open {port}: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False

def main():
    print("="*60)
    print("Side-A Direct Test")
    print("="*60)
    
    # Find ESP32 port
    port = find_esp32_port()
    if not port:
        print("\nWARNING: ESP32 port not found automatically")
        print("Checking common ports...")
        common_ports = ['COM3', 'COM4', 'COM5', 'COM7', 'COM8']
        for p in common_ports:
            try:
                s = serial.Serial(p, 115200, timeout=0.1)
                s.close()
                port = p
                print(f"✓ Found available port: {port}")
                break
            except:
                pass
    
    if not port:
        print("\n✗ No ESP32 port found")
        print("\nAvailable ports:")
        ports = serial.tools.list_ports.comports()
        for p in ports:
            print(f"  {p.device} - {p.description}")
        return False
    
        print(f"\nOK: Using port: {port}")
    
    # Test different baud rates
    baud_rates = [115200, 9600, 230400]
    
    for baud in baud_rates:
        if test_port(port, baud):
            break
        time.sleep(1)
    
    print("\n" + "="*60)
    print("Test Complete")
    print("="*60)
    
    return True

if __name__ == "__main__":
    main()

