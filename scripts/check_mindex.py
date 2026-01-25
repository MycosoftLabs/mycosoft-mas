#!/usr/bin/env python3
"""Check MINDEX API status on VM"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import urllib3
import base64
import time

urllib3.disable_warnings()

PROXMOX_HOST = 'https://192.168.0.202:8006'
headers = {'Authorization': 'PVEAPIToken=myca@pve!mas=ca23b6c8-5746-46c4-8e36-fc6caad5a9e5'}

def exec_cmd(cmd, timeout=60):
    url = f'{PROXMOX_HOST}/api2/json/nodes/pve/qemu/103/agent/exec'
    data = {'command': '/bin/bash', 'input-data': cmd}
    r = requests.post(url, headers=headers, data=data, verify=False, timeout=15)
    if not r.ok:
        return None
    pid = r.json().get('data', {}).get('pid')
    if not pid:
        return None
    status_url = f'{PROXMOX_HOST}/api2/json/nodes/pve/qemu/103/agent/exec-status?pid={pid}'
    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
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
    return None

print('Checking all running containers...')
out = exec_cmd('docker ps --format "{{.Names}} {{.Status}}" | head -15')
print(out)

print('\nChecking MINDEX API on port 8000...')
out = exec_cmd('curl -s http://localhost:8000/api/mindex/stats 2>/dev/null | head -c 200 || echo "MINDEX API NOT RUNNING"')
print(f'Result: {out}')

print('\nChecking docker-compose file for MINDEX...')
out = exec_cmd('cat /home/mycosoft/mycosoft/mas/docker-compose.always-on.yml | grep -A5 "mindex-api" || echo "mindex-api not found in compose"')
print(out)
