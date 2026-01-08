# Complete MycoBrain Testing Script
# Tests all NeoPixel, Buzzer, and Device Manager features

Write-Host "=== MYCOBRAIN COMPLETE TEST ===" -ForegroundColor Cyan

# Check if board is connected
$ports = python -c "import serial.tools.list_ports; ports = [p.device for p in serial.tools.list_ports.comports() if p.vid == 12346]; print('\n'.join(ports))" 2>&1
$comPort = ($ports -split "`n" | Where-Object { $_ -match "COM\d+" } | Select-Object -First 1).Trim()

if (-not $comPort) {
    Write-Host "No ESP32-S3 board found!" -ForegroundColor Red
    exit 1
}

Write-Host "Found board on: $comPort" -ForegroundColor Green

# Test commands
Write-Host "`n=== Testing Commands ===" -ForegroundColor Yellow

python -c @"
import serial
import time
import json

ser = serial.Serial('$comPort', 115200, timeout=3)
time.sleep(2)

# Clear buffer
if ser.in_waiting:
    ser.read(ser.in_waiting)

print('1. Testing STATUS command...')
ser.write(b'status\n')
time.sleep(0.5)
if ser.in_waiting:
    print('   ', ser.read(ser.in_waiting).decode('utf-8', errors='ignore').strip())

print('2. Testing LED RED (plaintext)...')
ser.write(b'led red\n')
time.sleep(0.5)
if ser.in_waiting:
    print('   ', ser.read(ser.in_waiting).decode('utf-8', errors='ignore').strip())

print('3. Testing LED GREEN (plaintext)...')
ser.write(b'led green\n')
time.sleep(0.5)
if ser.in_waiting:
    print('   ', ser.read(ser.in_waiting).decode('utf-8', errors='ignore').strip())

print('4. Testing BUZZER BEEP (plaintext)...')
ser.write(b'buzzer beep\n')
time.sleep(0.5)
if ser.in_waiting:
    print('   ', ser.read(ser.in_waiting).decode('utf-8', errors='ignore').strip())

print('5. Testing JSON set_neopixel command...')
# Format that website might send
jsonCmd = '{\"command\":\"set_neopixel\",\"parameters\":{\"r\":0,\"g\":0,\"b\":255}}\n'
ser.write(jsonCmd.encode())
time.sleep(0.5)
if ser.in_waiting:
    print('   ', ser.read(ser.in_waiting).decode('utf-8', errors='ignore').strip())

print('6. Testing JSON set_buzzer command...')
jsonCmd2 = '{\"command\":\"set_buzzer\",\"parameters\":{\"frequency\":2000,\"duration\":300}}\n'
ser.write(jsonCmd2.encode())
time.sleep(0.5)
if ser.in_waiting:
    print('   ', ser.read(ser.in_waiting).decode('utf-8', errors='ignore').strip())

print('7. Testing I2C scan...')
ser.write(b'scan\n')
time.sleep(0.5)
if ser.in_waiting:
    print('   ', ser.read(ser.in_waiting).decode('utf-8', errors='ignore').strip())

print('8. LED OFF...')
ser.write(b'led off\n')
time.sleep(0.5)
if ser.in_waiting:
    print('   ', ser.read(ser.in_waiting).decode('utf-8', errors='ignore').strip())

ser.close()
print('\n=== All tests complete ===')
"@

Write-Host "`n=== Testing via Service API ===" -ForegroundColor Yellow

# Test via service
python -c @"
import requests
import time

base = 'http://localhost:8003'

# Check service health
try:
    health = requests.get(f'{base}/health', timeout=2)
    print('Service health:', health.json())
except Exception as e:
    print(f'Service not running: {e}')
    exit(1)

# Get devices
devices = requests.get(f'{base}/devices').json()
print(f'Connected devices: {len(devices.get(\"devices\", []))}')

if devices.get('devices'):
    device_id = devices['devices'][0]['device_id']
    print(f'Using device: {device_id}')
    
    # Test commands via API
    print('\n1. Testing set_neopixel via API...')
    cmd1 = requests.post(f'{base}/devices/{device_id}/command', json={
        'command': {'command_type': 'set_neopixel', 'r': 255, 'g': 0, 'b': 0}
    })
    print('   Response:', cmd1.json())
    
    time.sleep(0.5)
    
    print('2. Testing set_buzzer via API...')
    cmd2 = requests.post(f'{base}/devices/{device_id}/command', json={
        'command': {'command_type': 'set_buzzer', 'frequency': 1000, 'duration': 200}
    })
    print('   Response:', cmd2.json())
    
    time.sleep(0.5)
    
    print('3. Testing i2c_scan via API...')
    cmd3 = requests.post(f'{base}/devices/{device_id}/command', json={
        'command': {'command_type': 'i2c_scan'}
    })
    print('   Response:', cmd3.json())
else:
    print('No devices connected. Connect via website first.')
"@

Write-Host "`n=== Test Complete ===" -ForegroundColor Green
Write-Host "Check website at http://localhost:3000/natureos/devices" -ForegroundColor Cyan
