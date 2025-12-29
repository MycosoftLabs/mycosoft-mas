#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check if BME688 sensors are causing power issues
"""
import serial
import time

def check_power_with_sensors(port):
    """Check if board responds with BME688s connected."""
    print(f"\n{'='*60}")
    print(f"Testing {port} with BME688s connected")
    print(f"{'='*60}")
    
    try:
        s = serial.Serial(port, 115200, timeout=2)
        time.sleep(2)
        
        # Reset
        s.setDTR(False)
        s.setRTS(True)
        time.sleep(0.1)
        s.setDTR(True)
        s.setRTS(False)
        time.sleep(3)
        
        data = s.read(3000)
        s.close()
        
        if data:
            output = data.decode('utf-8', errors='ignore')
            print(f"Board responded: {len(data)} bytes")
            print(output[:500])
            
            if "BOD" in output or "brownout" in output.lower():
                print("\n*** POWER ISSUE DETECTED ***")
                print("BME688s may be drawing too much current!")
                return False
            else:
                print("\nBoard is responding - BME688s OK")
                return True
        else:
            print("\nNo response - board may be dead or shorted")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    ports = ["COM5", "COM7", "COM3", "COM4", "COM6", "COM8"]
    print("Checking which port has the bridged board...")
    
    for port in ports:
        try:
            check_power_with_sensors(port)
        except:
            pass

