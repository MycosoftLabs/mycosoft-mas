import serial
import time

ser = serial.Serial('COM5', 115200, timeout=2)
time.sleep(1)

# Clear buffer
ser.read(ser.in_waiting)

# Test ping
print('Sending ping...')
ser.write(b'{"cmd":"ping"}\n')
time.sleep(0.5)
resp = ser.readline().decode('utf-8', errors='ignore').strip()
print(f'Response: {resp if resp else "No response"}')

# Test status
print('Sending status...')
ser.write(b'{"cmd":"status"}\n')
time.sleep(0.5)
resp = ser.readline().decode('utf-8', errors='ignore').strip()
print(f'Response: {resp if resp else "No response"}')

# Test LED red
print('Sending LED red...')
ser.write(b'{"cmd":"led","r":255,"g":0,"b":0}\n')
time.sleep(0.5)
resp = ser.readline().decode('utf-8', errors='ignore').strip()
print(f'Response: {resp if resp else "No response"}')

# Test buzzer
print('Sending buzzer...')
ser.write(b'{"cmd":"buzzer","freq":1000,"dur":200}\n')
time.sleep(0.5)
resp = ser.readline().decode('utf-8', errors='ignore').strip()
print(f'Response: {resp if resp else "No response"}')

# Check remaining
time.sleep(1)
remaining = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
if remaining:
    print(f'Additional: {remaining[:500]}')

ser.close()
print('Done.')
