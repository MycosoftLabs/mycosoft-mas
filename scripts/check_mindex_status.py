#!/usr/bin/env python3
"""Check MINDEX container status"""
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
        return f'Request failed: {r.status_code}'
    pid = r.json().get('data', {}).get('pid')
    if not pid:
        return 'No PID'
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
    return 'Timeout'

print('=== All Docker Containers ===')
out = exec_cmd('docker ps -a --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}" | head -20')
print(out)

print('\n=== MINDEX Compose Services ===')
out = exec_cmd('cd /home/mycosoft/mindex-deploy && docker compose ps 2>&1')
print(out)

print('\n=== MINDEX API Logs ===')
out = exec_cmd('docker logs mindex-api --tail 20 2>&1')
print(out)

print('\n=== Direct API Test ===')
out = exec_cmd('curl -s http://localhost:8000/api/mindex/health 2>&1')
print(f'Health: {out}')

out = exec_cmd('curl -s http://localhost:8000/ 2>&1')
print(f'Root: {out}')
