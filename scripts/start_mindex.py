#!/usr/bin/env python3
"""Start MINDEX API and related services on VM"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import urllib3
import base64
import time

urllib3.disable_warnings()

PROXMOX_HOST = 'https://192.168.0.202:8006'
headers = {'Authorization': 'PVEAPIToken=myca@pve!mas=ca23b6c8-5746-46c4-8e36-fc6caad5a9e5'}

def exec_cmd(cmd, timeout=300):
    url = f'{PROXMOX_HOST}/api2/json/nodes/pve/qemu/103/agent/exec'
    data = {'command': '/bin/bash', 'input-data': cmd}
    r = requests.post(url, headers=headers, data=data, verify=False, timeout=15)
    if not r.ok:
        print(f'Request failed: {r.status_code}')
        return None
    pid = r.json().get('data', {}).get('pid')
    if not pid:
        print('No PID returned')
        return None
    status_url = f'{PROXMOX_HOST}/api2/json/nodes/pve/qemu/103/agent/exec-status?pid={pid}'
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(3)
        try:
            sr = requests.get(status_url, headers=headers, verify=False, timeout=10)
            if sr.ok:
                sd = sr.json().get('data', {})
                if sd.get('exited'):
                    out = sd.get('out-data', '')
                    try:
                        if out:
                            out = base64.b64decode(out).decode('utf-8', errors='replace')
                    except:
                        pass
                    return out
        except Exception as e:
            print(f'Polling error: {e}')
            continue
    return None

print('Step 1: Check if MINDEX folder exists on VM...')
out = exec_cmd('ls -la /home/mycosoft/MINDEX/mindex/ 2>&1 | head -5 || echo "MINDEX folder not found"')
print(out)

print('\nStep 2: Start MINDEX services (postgres, api, etl)...')
out = exec_cmd('cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml up -d mindex-postgres mindex-api 2>&1 | tail -20')
print(out)

print('\nStep 3: Wait for services to be healthy (30s)...')
time.sleep(30)

print('\nStep 4: Check MINDEX container status...')
out = exec_cmd('docker ps --filter name=mindex --format "{{.Names}} {{.Status}}"')
print(out)

print('\nStep 5: Test MINDEX API...')
out = exec_cmd('curl -s http://localhost:8000/api/mindex/stats 2>/dev/null | head -c 300 || echo "API NOT RESPONDING"')
print(f'Result: {out}')
