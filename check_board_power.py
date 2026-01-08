#!/usr/bin/env python3
"""Check MycoBrain board power status and boot messages"""
import serial
import serial.tools.list_ports
import time
import sys

def check_port(port_name, baud=115200, timeout=3):
    """Check if a port is accessible and read boot messages"""
    print(f"\n{'='*60}")
    print(f"Checking {port_name}...")
    print(f"{'='*60}")
    
    # Check if port exists
    ports = serial.tools.list_ports.comports()
    found = [p for p in ports if port_name in p.device]
    
    if not found:
        print(f"[ERROR] {port_name} NOT FOUND - Port may not be connected")
        return False
    
    port_info = found[0]
    print(f"[OK] Port detected: {port_info.device}")
    print(f"  Description: {port_info.description}")
    print(f"  VID: {port_info.vid:04X}, PID: {port_info.pid:04X}")
    
    # Try to open and read
    try:
        ser = serial.Serial(port_name, baud, timeout=timeout)
        print(f"[OK] Port opened successfully")
        
        # Wait a moment for any boot messages
        time.sleep(0.5)
        
        # Read any available data
        data = b""
        start_time = time.time()
        while time.time() - start_time < 2:
            if ser.in_waiting > 0:
                chunk = ser.read(ser.in_waiting)
                data += chunk
                time.sleep(0.1)
            else:
                time.sleep(0.1)
        
        if data:
            text = data.decode('utf-8', errors='ignore')
            print(f"\n[BOOT] Boot Messages ({len(data)} bytes):")
            print("-" * 60)
            print(text[:1000])  # First 1000 chars
            print("-" * 60)
            
            # Check for power-related indicators
            text_lower = text.lower()
            if 'brownout' in text_lower or 'brown' in text_lower:
                print("[WARNING] BROWNOUT DETECTED - Power issue!")
            if 'reset' in text_lower:
                print("[OK] Reset detected - Board is booting")
            if 'ets' in text_lower or 'esp32' in text_lower:
                print("[OK] ESP32 boot messages detected")
            if 'ready' in text_lower:
                print("[OK] Board appears ready")
        else:
            print("[WARNING] NO DATA RECEIVED")
            print("   Possible causes:")
            print("   - Board not powered (no LEDs = no power)")
            print("   - Board not booting")
            print("   - Wrong baud rate")
            print("   - Serial port locked by another process")
        
        ser.close()
        return True
        
    except serial.SerialException as e:
        print(f"[ERROR] Serial Error: {e}")
        if "could not open port" in str(e).lower():
            print("   Port may be locked by another process")
        elif "access denied" in str(e).lower():
            print("   Port access denied - may need admin or close other programs")
        return False
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("MycoBrain Power & Boot Diagnostics")
    print("="*60)
    
    # Check both ports
    com5_ok = check_port("COM5")
    time.sleep(1)
    com6_ok = check_port("COM6")
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"COM5 (Side A): {'[OK]' if com5_ok else '[ISSUE]'}")
    print(f"COM6 (Side B): {'[OK]' if com6_ok else '[ISSUE]'}")
    
    if not com5_ok and not com6_ok:
        print("\n[WARNING] POWER ISSUE DETECTED")
        print("\nRecommendations:")
        print("1. Check USB cable - must support data + power")
        print("2. Use USB 3.0 port or powered USB hub (2A+ recommended)")
        print("3. Try different USB cable")
        print("4. Check if board LEDs light up when powered")
        print("5. Verify USB ports provide adequate power")
    
    sys.exit(0 if (com5_ok or com6_ok) else 1)
