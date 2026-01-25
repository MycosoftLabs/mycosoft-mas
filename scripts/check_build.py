#!/usr/bin/env python3
"""Check build status on VM"""
import requests
import urllib3
import time
urllib3.disable_warnings()

headers = {'Authorization': 'PVEAPIToken=myca@pve!mas=ca23b6c8-5746-46c4-8e36-fc6caad5a9e5'}
PROXMOX = 'https://192.168.0.202:8006'

def exec_cmd(cmd, wait=10):
    data = {'command': '/bin/bash', 'input-data': cmd}
    r = requests.post(f'{PROXMOX}/api2/json/nodes/pve/qemu/103/agent/exec', headers=headers, data=data, verify=False, timeout=10)
    if not r.ok: return None
    pid = r.json().get('data', {}).get('pid')
    if not pid: return None
    time.sleep(wait)
    s = requests.get(f'{PROXMOX}/api2/json/nodes/pve/qemu/103/agent/exec-status', headers=headers, params={'pid': pid}, verify=False, timeout=10)
    if s.ok:
        data = s.json().get('data', {})
        return data.get('out-data', '') if data.get('exited') else 'still running...'
    return None

# Check if build is still running
print('Checking docker build processes:')
result = exec_cmd('ps aux | grep -E "docker.*build" | grep -v grep', 5)
print(result or 'None')

print('\nChecking buildx processes:')
result = exec_cmd('pgrep -af docker | head -5', 5)
print(result or 'None')

print('\nContainer creation time:')
result = exec_cmd('docker inspect mycosoft-always-on-mycosoft-website-1 --format "{{.Created}}"', 5)
print(result or 'None')
