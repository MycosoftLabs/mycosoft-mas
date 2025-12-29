#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the bridged board (was working before, now no light)
"""
import serial
import serial.tools.list_ports
import time

def find_esp32_ports():
    """Find all ESP32 ports."""
    ports = serial.tools.list_ports.comports()
    esp32_ports = []
    for p in ports:
        if '303A' in p.hwid:
            esp32_ports.append(p.device)
    return esp32_ports

def test_board(port):
    """Test a board thoroughly."""
    print(f"\n{'='*60}")
    print(f"Testing {port} (Bridged Board)")
    print(f"{'='*60}")
    
    # Initialize serial port variable before try block to avoid NameError in finally
    s = None
    
    try:
        s = serial.Serial(port, 115200, timeout=2)
        print(f"OK: Port opened")
        
        # Wait a bit
        time.sleep(2)
        
        # Try to reset
        s.setDTR(False)
        s.setRTS(True)
        time.sleep(0.1)
        s.setDTR(True)
        s.setRTS(False)
        time.sleep(2)
        
        # Read any data
        s.reset_input_buffer()
        data = s.read(3000)
        
        if data:
            output = data.decode('utf-8', errors='ignore')
            print(f"\nRECEIVED {len(data)} bytes:")
            print("-" * 60)
            print(output[:800])
            print("-" * 60)
            
            if "MINIMAL TEST" in output or "Hardware Check" in output:
                print("\n>>> STATUS: Firmware running - Board is working!")
                return "WORKING"
            elif "ESP-ROM" in output or "waiting for download" in output:
                print("\n>>> STATUS: In bootloader - Ready for upload")
                return "BOOTLOADER"
            elif "BOD" in output or "brownout" in output.lower():
                print("\n>>> STATUS: Power issue - Brownout detected")
                return "POWER_ISSUE"
            elif "rst:" in output.lower():
                print("\n>>> STATUS: Boot loop - Device resetting")
                return "BOOTLOOP"
            else:
                print("\n>>> STATUS: Unknown output")
                return "UNKNOWN"
        else:
            print("\n>>> STATUS: No output - Board may be:")
            print("    - In bootloader (silent)")
            print("    - Power issue (not enough power)")
            print("    - Bridge modification issue")
            return "NO_OUTPUT"
        
    except serial.SerialException as e:
        print(f"\nERROR: Cannot open {port}")
        print(f"  {e}")
        print("\nPossible causes:")
        print("  - Board not getting power (bridge issue?)")
        print("  - USB cable issue")
        print("  - Port in use")
        return "ERROR"
    except Exception as e:
        print(f"\nERROR: {e}")
        return "ERROR"
    finally:
        # Ensure serial port is always closed, even if an exception occurs
        if s is not None and s.is_open:
            try:
                s.close()
            except Exception as close_error:
                print(f"\nWARNING: Error closing serial port: {close_error}")

def main():
    print("="*60)
    print("Testing Bridged Board")
    print("="*60)
    print("\nThis board:")
    print("  - Has bridge modification (diode removed)")
    print("  - Was working before with Garrett's code")
    print("  - Now has NO light")
    print("  - Has 2 BME688 sensors connected")
    
    ports = find_esp32_ports()
    
    if not ports:
        print("\nWARNING: No ESP32 devices found!")
        print("Check:")
        print("  - USB cable is connected")
        print("  - Board is getting power")
        print("  - Bridge modification is correct")
        return
    
    print(f"\nFound {len(ports)} ESP32 device(s): {', '.join(ports)}")
    
    # Test the first port (assuming it's the bridged board)
    if ports:
        status = test_board(ports[0])
        
        print("\n" + "="*60)
        print("DIAGNOSIS")
        print("="*60)
        
        if status == "WORKING":
            print("\nBoard is working! Firmware is running.")
            print("The 'no light' might be normal if LED code isn't running.")
        elif status == "BOOTLOADER":
            print("\nBoard is in bootloader mode.")
            print("Upload firmware - it should work.")
        elif status == "POWER_ISSUE":
            print("\nPOWER ISSUE DETECTED")
            print("The bridge modification might be causing power problems.")
            print("Check:")
            print("  - Bridge connection is secure")
            print("  - No shorts from bridge")
            print("  - Power regulation is working")
        elif status == "NO_OUTPUT":
            print("\nNO OUTPUT - Possible issues:")
            print("  1. Bridge modification damaged power circuit")
            print("  2. Board not getting enough power")
            print("  3. USB cable/port issue")
            print("  4. Board needs external power")
        elif status == "ERROR":
            print("\nCannot communicate with board.")
            print("Hardware issue - check bridge modification.")

if __name__ == "__main__":
    main()

