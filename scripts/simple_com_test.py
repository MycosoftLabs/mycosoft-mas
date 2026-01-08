import serial
import time

port = 'COM6'
baud = 115200

print(f"Testing {port}...")
try:
    s = serial.Serial(port, baud, timeout=3)
    print("Connected!")
    time.sleep(2)
    
    # Clear buffer
    s.reset_input_buffer()
    
    # Send newline to trigger response
    s.write(b'\n')
    time.sleep(0.5)
    data = s.read_all()
    if data:
        print(f"Boot data: {data.decode('utf-8', errors='ignore')}")
    
    # Send status
    s.write(b'status\n')
    time.sleep(1)
    data = s.read_all()
    if data:
        print(f"Status: {data.decode('utf-8', errors='ignore')}")
    else:
        print("No response to status command")
    
    s.close()
    print("Test complete")
except Exception as e:
    print(f"Error: {e}")
