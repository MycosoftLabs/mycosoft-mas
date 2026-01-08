import serial
import time

for port in ['COM5', 'COM7']:
    try:
        print(f'\n=== {port} ===')
        ser = serial.Serial(port, 115200, timeout=2)
        output = b''
        for _ in range(30):
            if ser.in_waiting:
                output += ser.read(ser.in_waiting)
            time.sleep(0.3)
        if output:
            text = output.decode('utf-8', errors='ignore')
            print(f'{port} OUTPUT ({len(text)} chars):')
            print(text[:800])
            if 'MycoBrain' in text and 'Brownout' not in text:
                print(f'\n*** {port} WORKING! ***')
            elif 'Brownout' in text:
                print(f'\n{port}: BROWNOUT')
        else:
            print(f'{port}: No output')
        ser.close()
    except Exception as e:
        print(f'{port}: {e}')

print('\nCheck physically: NeoPixel ON? Beep played?')
