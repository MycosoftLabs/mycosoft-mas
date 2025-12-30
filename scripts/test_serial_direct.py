#!/usr/bin/env python3
"""Direct serial test for MycoBrain"""

import serial
import time
import json

print('Opening COM5...')
try:
    ser = serial.Serial('COM5', 115200, timeout=2)
    time.sleep(1)
    ser.reset_input_buffer()
    
    print('Reading any startup messages...')
    if ser.in_waiting > 0:
        startup = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
        print(f'Startup: {startup[:500]}')
    
    print('Sending status command...')
    ser.write(b'{"cmd":"status"}\n')
    ser.flush()
    time.sleep(0.5)
    
    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
        print(f'Response: {response}')
    else:
        print('No response from device')
    
    print('\nSending beep command...')
    ser.write(b'{"cmd":"beep","freq":1000,"ms":200}\n')
    ser.flush()
    time.sleep(0.5)
    
    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting).decode('utf-8', errors='replace')
        print(f'Beep response: {response}')
    
    ser.close()
    print('Done!')
except Exception as e:
    print(f'Error: {e}')

