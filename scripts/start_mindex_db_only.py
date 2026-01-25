#!/usr/bin/env python3
"""Start MINDEX PostgreSQL with existing data and check counts"""
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

print('Step 1: Stop any existing mindex-postgres container...')
out = exec_cmd('docker stop mindex-postgres-data 2>/dev/null; docker rm mindex-postgres-data 2>/dev/null; echo "Cleaned"')
print(out)

print('\nStep 2: Start mindex-postgres with existing volume...')
out = exec_cmd('''docker run -d --name mindex-postgres-data \\
  -e POSTGRES_DB=mindex \\
  -e POSTGRES_USER=mindex \\
  -e POSTGRES_PASSWORD=mindex \\
  -p 5434:5432 \\
  -v mycosoft-always-on_mindex_postgres_data:/var/lib/postgresql/data \\
  postgis/postgis:16-3.4 2>&1''')
print(out)

print('\nStep 3: Wait for postgres to start (15s)...')
time.sleep(15)

print('\nStep 4: Check database tables and counts...')
out = exec_cmd('''docker exec mindex-postgres-data psql -U mindex -d mindex -c "\\dt" 2>&1''')
print(f'Tables: {out}')

out = exec_cmd('''docker exec mindex-postgres-data psql -U mindex -d mindex -c "SELECT COUNT(*) as taxa_count FROM taxa;" 2>&1''')
print(f'Taxa count: {out}')

out = exec_cmd('''docker exec mindex-postgres-data psql -U mindex -d mindex -c "SELECT COUNT(*) as obs_count FROM observations;" 2>&1''')
print(f'Observations count: {out}')
