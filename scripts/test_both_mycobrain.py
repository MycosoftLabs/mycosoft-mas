#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test both MycoBrain boards
"""
import serial
import time

def test_board(port):
    """Test a single board."""
    print(f"\n{'='*60}")
    print(f"Testing {port}")
    print(f"{'='*60}")
    
    try:
        s = serial.Serial(port, 115200, timeout=2)
        print(f"OK: Port opened")
        
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
        data = s.read(3000)
        s.close()
        
        if data:
            output = data.decode('utf-8', errors='ignore')
            print(f"\nRECEIVED {len(data)} bytes:")
            print("-" * 60)
            print(output[:500])
            print("-" * 60)
            
            # Analyze
            if "MINIMAL TEST" in output or "Hardware Check" in output:
                print("\n>>> STATUS: Minimal test firmware running - Hardware OK!")
                return "WORKING"
            elif "SuperMorgIO" in output or "MycoBrain" in output:
                print("\n>>> STATUS: Main firmware running - Device working!")
                return "WORKING"
            elif "ESP-ROM" in output or "waiting for download" in output:
                print("\n>>> STATUS: In bootloader mode - Ready for upload")
                return "BOOTLOADER"
            elif "rst:" in output.lower():
                print("\n>>> STATUS: Boot loop detected - Device resetting")
                return "BOOTLOOP"
            else:
                print("\n>>> STATUS: Unknown output")
                return "UNKNOWN"
        else:
            print("\n>>> STATUS: No output - Device may be in bootloader or crashed")
            return "NO_OUTPUT"
            
    except serial.SerialException as e:
        print(f"\nERROR: Cannot open {port}")
        print(f"  {e}")
        return "ERROR"
    except Exception as e:
        print(f"\nERROR: {e}")
        return "ERROR"

def main():
    print("="*60)
    print("Testing Both MycoBrain Boards")
    print("="*60)
    
    ports = ['COM5', 'COM7']
    
    results = {}
    for port in ports:
        results[port] = test_board(port)
        time.sleep(1)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for port, status in results.items():
        print(f"\n{port}: {status}")
    
    print("\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)
    
    working = [p for p, s in results.items() if s == "WORKING"]
    bootloader = [p for p, s in results.items() if s == "BOOTLOADER"]
    
    if working:
        print(f"\nBoard(s) with GREEN LIGHT (working): {', '.join(working)}")
        print("  - These have firmware running")
        print("  - Open Serial Monitor to test commands")
    
    if bootloader:
        print(f"\nBoard(s) WITHOUT green light (bootloader): {', '.join(bootloader)}")
        print("  - These are ready for firmware upload")
        print("  - Upload MycoBrain_SideA_MINIMAL_TEST.ino")
        print("  - No need to put in boot mode - already there!")

if __name__ == "__main__":
    main()


