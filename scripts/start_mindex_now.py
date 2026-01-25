#!/usr/bin/env python3
"""Start MINDEX containers that were created but not running"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import urllib3
import base64
import time

urllib3.disable_warnings()

PROXMOX_HOST = 'https://192.168.0.202:8006'
headers = {'Authorization': 'PVEAPIToken=myca@pve!mas=ca23b6c8-5746-46c4-8e36-fc6caad5a9e5'}

def exec_cmd(cmd, timeout=120):
    url = f'{PROXMOX_HOST}/api2/json/nodes/pve/qemu/103/agent/exec'
    data = {'command': '/bin/bash', 'input-data': cmd}
    r = requests.post(url, headers=headers, data=data, verify=False, timeout=15)
    if not r.ok:
        return f'Request failed: {r.status_code}'
    pid = r.json().get('data', {}).get('pid')
    if not pid:
        return 'No PID'
    status_url = f'{PROXMOX_HOST}/api2/json/nodes/pve/qemu/103/agent/exec-status?pid={pid}'
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
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
        except:
            continue
    return 'Timeout'

print('Step 1: Remove old containers...')
out = exec_cmd('docker rm -f mindex-api mindex-postgres 2>/dev/null; echo "Cleaned"')
print(out)

print('\nStep 2: Start services with docker compose up...')
out = exec_cmd('cd /home/mycosoft/mindex-deploy && docker compose up -d 2>&1')
print(out)

print('\nStep 3: Wait 30s for services...')
time.sleep(30)

print('\nStep 4: Check container status...')
out = exec_cmd('docker ps --filter name=mindex --format "{{.Names}} {{.Status}}"')
print(out)

print('\nStep 5: Check mindex-postgres logs...')
out = exec_cmd('docker logs mindex-postgres --tail 10 2>&1')
print(out)

print('\nStep 6: Check mindex-api logs...')
out = exec_cmd('docker logs mindex-api --tail 15 2>&1')
print(out)

print('\nStep 7: Test API health...')
out = exec_cmd('curl -s http://localhost:8000/api/mindex/health 2>&1 || echo "FAILED"')
print(f'Health: {out}')

print('\nStep 8: Test API stats...')
out = exec_cmd('curl -s http://localhost:8000/api/mindex/stats 2>&1 | head -c 500 || echo "FAILED"')
print(f'Stats: {out}')
