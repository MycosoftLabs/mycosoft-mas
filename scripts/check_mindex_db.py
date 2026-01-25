#!/usr/bin/env python3
"""Check if MINDEX PostgreSQL has data"""
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

print('Check if mycosoft-postgres (main) has MINDEX tables...')
out = exec_cmd('''docker exec mycosoft-postgres psql -U mycosoft -d mycosoft -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE '%taxa%' OR table_name LIKE '%observation%' LIMIT 10;" 2>&1''')
print(out)

print('\nCheck docker volumes for mindex data...')
out = exec_cmd('docker volume ls | grep -i mindex')
print(out)

print('\nCheck if we can start mindex-postgres standalone...')
out = exec_cmd('docker run -d --name mindex-postgres-test -e POSTGRES_DB=mindex -e POSTGRES_USER=mindex -e POSTGRES_PASSWORD=mindex postgis/postgis:16-3.4 2>&1 && sleep 5 && docker logs mindex-postgres-test --tail 5 && docker rm -f mindex-postgres-test')
print(out)
