# Complete MycoBrain Feature Test
# Tests NeoPixel, Buzzer, I2C, and Device Manager integration

Write-Host "=== MYCOBRAIN COMPLETE FEATURE TEST ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check board connection
Write-Host "Step 1: Checking board connection..." -ForegroundColor Yellow
$ports = python -c "import serial.tools.list_ports; ports = [p.device for p in serial.tools.list_ports.comports() if p.vid == 12346]; print('\n'.join(ports))" 2>&1
$comPort = ($ports -split "`n" | Where-Object { $_ -match "COM\d+" } | Select-Object -First 1).Trim()

if (-not $comPort) {
    Write-Host "  ❌ No ESP32-S3 board found!" -ForegroundColor Red
    exit 1
}

Write-Host "  ✅ Found board on: $comPort" -ForegroundColor Green

# Step 2: Test direct serial commands
Write-Host "`nStep 2: Testing direct serial commands..." -ForegroundColor Yellow

python -c @"
import serial
import time

ser = serial.Serial('$comPort', 115200, timeout=3)
time.sleep(2)

# Clear buffer
if ser.in_waiting:
    ser.read(ser.in_waiting)

tests = [
    ('STATUS', b'status\n'),
    ('LED RED', b'led red\n'),
    ('LED GREEN', b'led green\n'),
    ('LED BLUE', b'led blue\n'),
    ('BUZZER BEEP', b'buzzer beep\n'),
    ('BUZZER COIN', b'buzzer coin\n'),
    ('I2C SCAN', b'scan\n'),
    ('LED OFF', b'led off\n'),
]

print('  Testing commands:')
for name, cmd in tests:
    ser.write(cmd)
    time.sleep(0.5)
    if ser.in_waiting:
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore').strip()
        if 'ok' in response.lower() or 'status' in response.lower():
            print(f'    ✅ {name}')
        else:
            print(f'    ⚠️  {name}: {response[:50]}')
    else:
        print(f'    ❌ {name}: No response')

ser.close()
"@

# Step 3: Test via service API
Write-Host "`nStep 3: Testing via MycoBrain Service API..." -ForegroundColor Yellow

python -c @"
import requests
import time

base = 'http://localhost:8003'

try:
    # Check service
    health = requests.get(f'{base}/health', timeout=2)
    if health.status_code == 200:
        print('  ✅ Service is running')
    else:
        print(f'  ❌ Service health check failed: {health.status_code}')
        exit(1)
except Exception as e:
    print(f'  ❌ Service not running: {e}')
    print('  Start service with: python -m uvicorn services.mycobrain.mycobrain_dual_service:app --port 8003')
    exit(1)

# Get devices
try:
    devices_resp = requests.get(f'{base}/devices', timeout=2)
    devices = devices_resp.json()
    device_list = devices.get('devices', [])
    
    if not device_list:
        print('  ⚠️  No devices connected. Connect via website first.')
        print('  Go to: http://localhost:3000/natureos/devices')
        exit(0)
    
    device_id = device_list[0]['device_id']
    print(f'  ✅ Found device: {device_id}')
    
    # Test commands
    print('  Testing API commands:')
    
    # NeoPixel Red
    try:
        resp = requests.post(f'{base}/devices/{device_id}/command', json={
            'command': {'command_type': 'set_neopixel', 'r': 255, 'g': 0, 'b': 0}
        }, timeout=5)
        if resp.status_code == 200:
            print('    ✅ set_neopixel (red)')
        else:
            print(f'    ❌ set_neopixel: {resp.status_code} - {resp.text[:100]}')
    except Exception as e:
        print(f'    ❌ set_neopixel error: {e}')
    
    time.sleep(0.5)
    
    # NeoPixel Green
    try:
        resp = requests.post(f'{base}/devices/{device_id}/command', json={
            'command': {'command_type': 'set_neopixel', 'r': 0, 'g': 255, 'b': 0}
        }, timeout=5)
        if resp.status_code == 200:
            print('    ✅ set_neopixel (green)')
        else:
            print(f'    ❌ set_neopixel: {resp.status_code}')
    except Exception as e:
        print(f'    ❌ set_neopixel error: {e}')
    
    time.sleep(0.5)
    
    # Buzzer
    try:
        resp = requests.post(f'{base}/devices/{device_id}/command', json={
            'command': {'command_type': 'set_buzzer', 'frequency': 1000, 'duration': 200}
        }, timeout=5)
        if resp.status_code == 200:
            print('    ✅ set_buzzer')
        else:
            print(f'    ❌ set_buzzer: {resp.status_code}')
    except Exception as e:
        print(f'    ❌ set_buzzer error: {e}')
    
    time.sleep(0.5)
    
    # I2C Scan
    try:
        resp = requests.post(f'{base}/devices/{device_id}/command', json={
            'command': {'command_type': 'i2c_scan'}
        }, timeout=5)
        if resp.status_code == 200:
            print('    ✅ i2c_scan')
        else:
            print(f'    ❌ i2c_scan: {resp.status_code}')
    except Exception as e:
        print(f'    ❌ i2c_scan error: {e}')
    
    # Get telemetry
    try:
        resp = requests.get(f'{base}/devices/{device_id}/telemetry', timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('status') == 'ok':
                print('    ✅ telemetry')
            else:
                print(f'    ⚠️  telemetry: {data}')
        else:
            print(f'    ❌ telemetry: {resp.status_code}')
    except Exception as e:
        print(f'    ❌ telemetry error: {e}')
    
except Exception as e:
    print(f'  ❌ Error: {e}')
"@

# Step 4: Instructions
Write-Host "`nStep 4: Website Testing Instructions" -ForegroundColor Yellow
Write-Host "  1. Open: http://localhost:3000/natureos/devices" -ForegroundColor Cyan
Write-Host "  2. Click 'MycoBrain Devices' tab" -ForegroundColor Cyan
Write-Host "  3. Connect to $comPort (Side-A)" -ForegroundColor Cyan
Write-Host "  4. Test NeoPixel controls (Red, Green, Blue buttons)" -ForegroundColor Cyan
Write-Host "  5. Test Buzzer controls (Beep, Melody buttons)" -ForegroundColor Cyan
Write-Host "  6. Check Sensors tab for I2C devices" -ForegroundColor Cyan

Write-Host "`n=== Test Complete ===" -ForegroundColor Green
