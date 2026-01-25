#!/usr/bin/env python3
"""Find MINDEX codebase on VM"""
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

print('Searching for MINDEX codebase...')
out = exec_cmd('find /home -name "Dockerfile" -path "*mindex*" 2>/dev/null || echo "None found"')
print(f'Dockerfiles with mindex: {out}')

out = exec_cmd('find /home -name "main.py" -path "*mindex*" 2>/dev/null | head -5 || echo "None found"')  
print(f'main.py in mindex: {out}')

out = exec_cmd('ls -la /home/mycosoft/ 2>/dev/null | head -20')
print(f'Home directory: {out}')

out = exec_cmd('ls -la /opt/mycosoft/ 2>/dev/null | head -10')
print(f'Opt directory: {out}')
