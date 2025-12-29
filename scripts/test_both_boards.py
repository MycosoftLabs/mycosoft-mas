#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test both MycoBrain boards
"""
import serial
import serial.tools.list_ports
import time

def find_esp32_ports():
    """Find all ESP32-S3 ports."""
    ports = serial.tools.list_ports.comports()
    esp32_ports = []
    for p in ports:
        if '303A' in p.hwid or 'ESP' in p.description.upper():
            esp32_ports.append(p.device)
    return esp32_ports

def test_port(port, timeout=3):
    """Test a port for activity."""
    try:
        s = serial.Serial(port, 115200, timeout=1)
        time.sleep(2)
        s.reset_input_buffer()
        
        # Send reset
        s.setDTR(False)
        s.setRTS(True)
        time.sleep(0.1)
        s.setDTR(True)
        s.setRTS(False)
        time.sleep(1)
        
        # Read data
        data = s.read(2000)
        s.close()
        
        if data:
            output = data.decode('utf-8', errors='ignore')
            return output
        return None
    except Exception as e:
        return f"ERROR: {e}"

def main():
    print("="*60)
    print("Testing Both MycoBrain Boards")
    print("="*60)
    
    ports = find_esp32_ports()
    
    if len(ports) < 2:
        print(f"\nWARNING: Found only {len(ports)} ESP32 device(s)")
        print("Expected 2 devices (one with green light, one without)")
        print("\nAvailable ports:")
        all_ports = serial.tools.list_ports.comports()
        for p in all_ports:
            print(f"  {p.device} - {p.description}")
    
    print(f"\nFound {len(ports)} ESP32 device(s):")
    for i, port in enumerate(ports, 1):
        print(f"  {i}. {port}")
    
    print("\n" + "="*60)
    print("Testing each device...")
    print("="*60)
    
    results = {}
    for port in ports:
        print(f"\nTesting {port}...")
        result = test_port(port)
        results[port] = result
        
        if result:
            if "ERROR" in result:
                print(f"  {result}")
            elif "MINIMAL TEST" in result or "Hardware Check" in result:
                print("  STATUS: Minimal test firmware running - Hardware OK!")
            elif "SuperMorgIO" in result or "MycoBrain" in result:
                print("  STATUS: Main firmware running - Device working!")
            elif "ESP-ROM" in result or "waiting for download" in result:
                print("  STATUS: In bootloader mode - Ready for upload")
            elif "rst:" in result.lower():
                print("  STATUS: Boot loop detected - Device resetting")
            else:
                print(f"  STATUS: Unknown - Output: {result[:100]}")
        else:
            print("  STATUS: No output - Device may be in bootloader or crashed")
    
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print("\nBoard with GREEN LIGHT:")
    print("  - This board likely has firmware running")
    print("  - Should show serial output")
    print("\nBoard WITHOUT green light:")
    print("  - May not have firmware")
    print("  - May be in bootloader mode")
    print("  - May need firmware upload")
    
    print("\n" + "="*60)
    print("Recommendations")
    print("="*60)
    for port, result in results.items():
        print(f"\n{port}:")
        if result and "waiting for download" in result:
            print("  -> Upload firmware (device is ready)")
        elif result and ("MINIMAL TEST" in result or "SuperMorgIO" in result):
            print("  -> Device is working! Test commands in Serial Monitor")
        elif not result or "ERROR" in str(result):
            print("  -> Check connection, try uploading firmware")

if __name__ == "__main__":
    main()

