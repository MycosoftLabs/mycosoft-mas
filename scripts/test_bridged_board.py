#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the bridged board - check if it's alive even without light
"""
import serial
import serial.tools.list_ports
import time

def find_mycobrain_ports():
    """Find all COM ports that might be MycoBrain boards."""
    ports = []
    for port in serial.tools.list_ports.comports():
        if 'USB' in port.description.upper() or 'SERIAL' in port.description.upper():
            ports.append(port.device)
    return ports

def test_port(port):
    """Test if a port responds."""
    print(f"\n{'='*60}")
    print(f"Testing {port}")
    print(f"{'='*60}")
    
    try:
        s = serial.Serial(port, 115200, timeout=2)
        time.sleep(2)
        
        # Try to reset it
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
            print(f"RECEIVED {len(data)} bytes:")
            print("-" * 60)
            print(output[:1000])
            print("-" * 60)
            
            if "ESP-ROM" in output or "rst:" in output:
                print("\n>>> STATUS: Board is ALIVE - responding to reset")
                print(">>> Board is in bootloader or booting")
                return True
            elif "MINIMAL TEST" in output or "Loop running" in output:
                print("\n>>> STATUS: Board is RUNNING firmware!")
                return True
            else:
                print("\n>>> STATUS: Board sent data but unclear state")
                return True
        else:
            print("\n>>> STATUS: No data - board may be dead or not powered")
            return False
            
    except serial.SerialException as e:
        print(f"\n>>> ERROR: {e}")
        return False
    except Exception as e:
        print(f"\n>>> ERROR: {type(e).__name__}: {e}")
        return False
    finally:
        try:
            s.close()
        except:
            pass

def main():
    print("="*60)
    print("Testing Bridged Board (No Light)")
    print("="*60)
    print("\nThe bridged board should still respond via serial")
    print("even if the LED is not working.")
    print("\nScanning for COM ports...")
    
    ports = find_mycobrain_ports()
    
    if not ports:
        print("\nNo COM ports found!")
        print("\nTrying to detect any serial device...")
        all_ports = [p.device for p in serial.tools.list_ports.comports()]
        if all_ports:
            print(f"Found ports: {', '.join(all_ports)}")
            ports = all_ports
        else:
            print("No serial devices detected at all!")
            return
    
    print(f"\nFound {len(ports)} port(s): {', '.join(ports)}")
    print("\nTesting each port...")
    
    alive_ports = []
    for port in ports:
        if test_port(port):
            alive_ports.append(port)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    if alive_ports:
        print(f"\nBoards that responded: {', '.join(alive_ports)}")
        print("\nThe bridged board IS alive - it's just not showing a light!")
        print("This could be:")
        print("  1. LED circuit issue (not critical)")
        print("  2. Power LED not connected")
        print("  3. LED pin configuration issue")
    else:
        print("\nNo boards responded!")
        print("\nPossible issues:")
        print("  1. Board not getting power")
        print("  2. USB cable issue")
        print("  3. Bridge connection broken")
        print("  4. BME688 sensors causing short circuit")

if __name__ == "__main__":
    main()
