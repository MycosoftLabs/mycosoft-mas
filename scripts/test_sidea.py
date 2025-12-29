#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Side-A firmware functionality
"""
import serial
import time
import sys

def test_serial_commands(port="COM7", baud=115200):
    """Test Side-A via serial commands."""
    print("="*60)
    print("Side-A Firmware Test")
    print("="*60)
    
    try:
        s = serial.Serial(port, baud, timeout=2)
        print(f"\nConnected to {port} at {baud} baud")
        print("Waiting for boot messages...")
        time.sleep(3)
        
        # Read initial boot output
        s.reset_input_buffer()
        time.sleep(0.5)
        initial = s.read(2000)
        if initial:
            print("\n=== BOOT OUTPUT ===")
            print(initial.decode('utf-8', errors='ignore')[:500])
        
        # Test commands
        commands = [
            ("help", "Show help"),
            ("status", "Check sensor status"),
            ("scan", "I2C scan"),
            ("led rgb 0 255 0", "Set LED green"),
            ("coin", "Play coin sound"),
        ]
        
        print("\n" + "="*60)
        print("Testing Commands")
        print("="*60)
        
        for cmd, desc in commands:
            print(f"\n[{desc}] Sending: {cmd}")
            s.write((cmd + "\r\n").encode())
            time.sleep(1)
            
            response = s.read(1000)
            if response:
                output = response.decode('utf-8', errors='ignore')
                print(f"Response: {output[:200]}")
            else:
                print("No response")
            time.sleep(0.5)
        
        # Test buzzer
        print("\n" + "="*60)
        print("Testing Buzzer")
        print("="*60)
        buzzer_commands = ["morgio", "coin", "bump", "power", "1up"]
        for cmd in buzzer_commands:
            print(f"\nPlaying: {cmd}")
            s.write((cmd + "\r\n").encode())
            time.sleep(2)  # Wait for sound to play
        
        # Test LED colors
        print("\n" + "="*60)
        print("Testing LED Colors")
        print("="*60)
        colors = [
            ("255 0 0", "Red"),
            ("0 255 0", "Green"),
            ("0 0 255", "Blue"),
            ("255 255 0", "Yellow"),
            ("255 0 255", "Magenta"),
            ("0 255 255", "Cyan"),
        ]
        for rgb, name in colors:
            print(f"\nSetting LED to {name} ({rgb})")
            s.write(f"led rgb {rgb}\r\n".encode())
            time.sleep(1)
        
        # Final status
        print("\n" + "="*60)
        print("Final Status Check")
        print("="*60)
        s.write("status\r\n".encode())
        time.sleep(1)
        final = s.read(2000)
        if final:
            print(final.decode('utf-8', errors='ignore'))
        
        s.close()
        print("\n" + "="*60)
        print("Test Complete!")
        print("="*60)
        return True
        
    except serial.SerialException as e:
        print(f"\nERROR: Could not open {port}")
        print(f"  {e}")
        print("\nMake sure:")
        print("  - Device is connected to COM7")
        print("  - Serial Monitor is closed")
        print("  - Device is powered on")
        return False
    except Exception as e:
        print(f"\nERROR: {e}")
        return False

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else "COM7"
    test_serial_commands(port)

