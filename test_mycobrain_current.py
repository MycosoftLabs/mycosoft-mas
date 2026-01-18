import serial
import time
import requests

print("=== MycoBrain Current State Test ===\n")

# Test COM3
try:
    ser = serial.Serial('COM3', 115200, timeout=2)
    print("COM3: Connected")
    time.sleep(2)
    
    # Send status
    ser.write(b'status\r\n')
    ser.flush()
    time.sleep(1)
    
    output = b''
    for _ in range(20):
        if ser.in_waiting:
            output += ser.read(ser.in_waiting)
        time.sleep(0.2)
    
    if output:
        text = output.decode('utf-8', errors='ignore')
        print(f"Response: {text[:800]}")
        if 'MycoBrain' in text or 'BME' in text:
            print("\n*** COM3 WORKING! ***")
    else:
        print("No response")
    
    ser.close()
except Exception as e:
    print(f"COM3: {e}")

# Test service
print("\n=== Testing Service ===")
try:
    resp = requests.get('http://localhost:8003/health', timeout=2)
    print(f"Service: {resp.status_code} - {resp.json()}")
except:
    print("Service not responding")

# Test website
print("\n=== Testing Website ===")
try:
    resp = requests.get('http://localhost:3000', timeout=2)
    print(f"Website: {resp.status_code} - Running")
except:
    print("Website not responding")
