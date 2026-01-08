"""
MycoBrain Device Diagnostics
Tests device connection and provides troubleshooting info
"""

import serial
import time
import sys

def test_baud_rates(port):
    """Test different baud rates"""
    baud_rates = [115200, 9600, 57600, 38400, 19200]
    print(f"\nTesting different baud rates on {port}...")
    
    for baud in baud_rates:
        try:
            s = serial.Serial(port, baud, timeout=2)
            print(f"\n  Testing {baud} baud...")
            time.sleep(1)
            s.write(b'\n')
            time.sleep(0.5)
            data = s.read_all()
            if data:
                decoded = data.decode('utf-8', errors='ignore')
                print(f"    [OK] Got {len(data)} bytes: {decoded[:100]}")
                s.close()
                return baud
            s.close()
        except Exception as e:
            print(f"    [FAIL] {baud} baud: {e}")
    
    return None

def check_boot_messages(port, baud=115200):
    """Check for boot messages"""
    print(f"\nChecking for boot messages on {port}...")
    try:
        s = serial.Serial(port, baud, timeout=3)
        print("  Port opened, waiting 3 seconds for boot...")
        time.sleep(3)
        data = s.read_all()
        if data:
            decoded = data.decode('utf-8', errors='ignore')
            print(f"  [OK] Boot messages ({len(data)} bytes):")
            print(f"  {decoded[:300]}")
            return True
        else:
            print("  [WARN] No boot messages received")
            return False
        s.close()
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

def try_reset_sequence(port, baud=115200):
    """Try sending reset commands"""
    print(f"\nTrying reset sequence on {port}...")
    try:
        s = serial.Serial(port, baud, timeout=2)
        # Try various reset commands
        reset_cmds = [
            b'\x03',  # Ctrl+C
            b'\r\n',  # Enter
            b'reset\n',
            b'reboot\n',
            b'\n',
        ]
        
        for cmd in reset_cmds:
            print(f"  Sending: {cmd}")
            s.write(cmd)
            time.sleep(0.5)
            data = s.read_all()
            if data:
                print(f"    [OK] Response: {data.decode('utf-8', errors='ignore')[:100]}")
                s.close()
                return True
        
        s.close()
        return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

def main():
    port = 'COM6'
    
    print("="*60)
    print("MycoBrain Device Diagnostics")
    print("="*60)
    print(f"\nTesting port: {port}")
    
    # Test 1: Check boot messages
    has_boot = check_boot_messages(port)
    
    # Test 2: Try different baud rates
    working_baud = test_baud_rates(port)
    
    # Test 3: Try reset sequence
    reset_worked = try_reset_sequence(port, working_baud or 115200)
    
    # Summary
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    print(f"Boot messages: {'[OK] Yes' if has_boot else '[FAIL] No'}")
    print(f"Working baud rate: {working_baud or '[FAIL] None found'}")
    print(f"Reset response: {'[OK] Yes' if reset_worked else '[FAIL] No'}")
    
    if not has_boot and not working_baud and not reset_worked:
        print("\n[CRITICAL] Device appears to be unresponsive")
        print("\nTroubleshooting steps:")
        print("  1. Check if device LED is on (power indicator)")
        print("  2. Unplug and replug USB cable")
        print("  3. Try pressing RESET button on device")
        print("  4. Check Device Manager for COM port errors")
        print("  5. Verify firmware is flashed correctly")
        print("  6. Try different USB cable or port")
        print("  7. Check if device is in bootloader mode (hold BOOT, press RESET)")

if __name__ == "__main__":
    main()
