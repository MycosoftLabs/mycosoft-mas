#!/usr/bin/env python3
"""
MycoBrain Power and Connection Diagnostic
Checks if board is connected, powered, and communicating
"""

import serial
import serial.tools.list_ports
import time
import sys

def find_esp32_ports():
    """Find all ESP32 ports"""
    ports = []
    for p in serial.tools.list_ports.comports():
        # ESP32-S3 native USB: VID 0x303A
        # CP2102/CH340 bridge: various VIDs
        if p.vid == 0x303A or "USB Serial" in p.description or "CP210" in p.description:
            ports.append({
                "port": p.device,
                "description": p.description,
                "vid": hex(p.vid) if p.vid else None,
                "pid": hex(p.pid) if p.pid else None,
                "hwid": p.hwid
            })
    return ports

def test_serial_connection(port, baud=115200, timeout=3):
    """Test if we can communicate with the board"""
    print(f"\nTesting {port} at {baud} baud...")
    
    try:
        ser = serial.Serial(port, baud, timeout=timeout)
        time.sleep(0.5)  # Allow time for connection
        
        # Clear any buffered data
        ser.reset_input_buffer()
        
        # Check for any spontaneous output (boot messages, telemetry)
        print("  Waiting for any output (3 seconds)...")
        start = time.time()
        output = ""
        while time.time() - start < 3:
            if ser.in_waiting > 0:
                chunk = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
                output += chunk
                print(f"    Received: {repr(chunk[:100])}")
            time.sleep(0.1)
        
        if output:
            print(f"  [OK] Board is outputting data!")
            if "brownout" in output.lower():
                print("  [WARNING] Brownout detected! Power issue.")
            if "boot" in output.lower() or "hello" in output.lower():
                print("  [OK] Boot message detected - firmware is running")
        else:
            print("  [INFO] No spontaneous output")
        
        # Try sending a command
        print("  Sending 'status' command...")
        ser.write(b'status\n')
        ser.flush()
        time.sleep(0.5)
        
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
            print(f"  [OK] Response: {response[:200]}")
            return True
        else:
            print("  [INFO] No response to status command")
        
        # Try JSON command
        print("  Sending JSON command...")
        ser.write(b'{"cmd":"ping"}\n')
        ser.flush()
        time.sleep(0.5)
        
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
            print(f"  [OK] Response: {response[:200]}")
            return True
        else:
            print("  [WARNING] No response to JSON command")
        
        # Try to trigger LED blink
        print("  Sending LED command...")
        ser.write(b'{"cmd":"set_neopixel","led_index":0,"r":0,"g":255,"b":0}\n')
        ser.flush()
        time.sleep(0.5)
        
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
            print(f"  [OK] LED response: {response[:100]}")
        
        ser.close()
        return False
        
    except serial.SerialException as e:
        print(f"  [ERROR] Cannot open port: {e}")
        if "Access is denied" in str(e):
            print("  [FIX] Close Arduino IDE, Serial Monitor, or other apps using this port")
        return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

def main():
    print("=" * 60)
    print("MycoBrain Power & Connection Diagnostic")
    print("=" * 60)
    
    # Find ESP32 ports
    print("\n1. Scanning for ESP32 devices...")
    ports = find_esp32_ports()
    
    if not ports:
        print("  [ERROR] No ESP32 devices found!")
        print("\n  Possible causes:")
        print("    - Board not plugged in")
        print("    - USB cable is charge-only (no data)")
        print("    - Board has no power (check USB connection)")
        print("    - Driver not installed")
        print("    - Board in boot mode (hold BOOT, release RESET)")
        return
    
    print(f"  Found {len(ports)} device(s):")
    for p in ports:
        print(f"    {p['port']}: {p['description']}")
        print(f"      VID: {p['vid']}, PID: {p['pid']}")
    
    # Test each port
    print("\n2. Testing serial communication...")
    working_ports = []
    for p in ports:
        if test_serial_connection(p['port']):
            working_ports.append(p['port'])
    
    # Summary
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    if working_ports:
        print(f"[OK] Board is responding on: {', '.join(working_ports)}")
        print("\nIf LED is still not on, the firmware may need:")
        print("  1. Re-upload with correct settings (see ARDUINO_IDE_SETTINGS.md)")
        print("  2. Check if LED pins (12, 13, 14) are properly connected")
        print("  3. The 'led rgb 0 255 0' command to manually turn on green")
    else:
        print("[WARNING] Board detected but not responding")
        print("\nPossible issues:")
        print("  1. POWER ISSUE - The diode bridge modification may have caused a problem")
        print("     - Check if the board powers on at all (any LED activity)")
        print("     - Try a different USB port or powered USB hub")
        print("     - The brownout detector may be triggering")
        print()
        print("  2. FIRMWARE ISSUE - No firmware or corrupt flash")
        print("     - Try uploading minimal blink sketch first")
        print("     - Use boot mode: hold BOOT, plug in USB, release BOOT")
        print()
        print("  3. USB ISSUE - Wrong USB port or cable")
        print("     - MycoBrain has TWO USB-C ports (Side-A and Side-B)")
        print("     - Make sure you're connected to Side-A for sensor operations")
        print("     - Use a data-capable USB cable")
    
    print()

if __name__ == "__main__":
    main()

