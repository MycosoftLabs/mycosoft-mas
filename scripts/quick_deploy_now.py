#!/usr/bin/env python3
"""Quick deployment script to start container after build"""
import requests
import urllib3
import time
import base64
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PROXMOX_HOST = 'https://192.168.0.202:8006'
PROXMOX_TOKEN_ID = 'myca@pve!mas'
PROXMOX_TOKEN_SECRET = 'ca23b6c8-5746-46c4-8e36-fc6caad5a9e5'
PROXMOX_NODE = 'pve'
VM_ID = 103

headers = {'Authorization': f'PVEAPIToken={PROXMOX_TOKEN_ID}={PROXMOX_TOKEN_SECRET}'}

def exec_cmd(cmd, timeout=180):
    url = f'{PROXMOX_HOST}/api2/json/nodes/{PROXMOX_NODE}/qemu/{VM_ID}/agent/exec'
    data = {'command': '/bin/bash', 'input-data': cmd}
    r = requests.post(url, headers=headers, data=data, verify=False, timeout=15)
    pid = r.json().get('data', {}).get('pid')
    
    status_url = f'{PROXMOX_HOST}/api2/json/nodes/{PROXMOX_NODE}/qemu/{VM_ID}/agent/exec-status?pid={pid}'
    start = time.time()
    
    while time.time() - start < timeout:
        time.sleep(3)
        try:
            sr = requests.get(status_url, headers=headers, verify=False, timeout=15)
            if sr.ok:
                sd = sr.json().get('data', {})
                if sd.get('exited'):
                    out = sd.get('out-data', '')
                    try:
                        out = base64.b64decode(out).decode('utf-8', errors='replace') if out else ''
                    except:
                        pass
                    return out
        except Exception as e:
            print(f'Polling...')
    return 'TIMEOUT'

# Start container with NAS volume mount
print('=== Starting container with NAS volume mount ===')
result = exec_cmd('''docker run -d --name mycosoft-website -p 3000:3000 --restart unless-stopped -v /opt/mycosoft/media/website/assets:/app/public/assets:ro mycosoft-always-on-mycosoft-website:latest''', timeout=120)
print(result)

print()
print('=== Waiting 20 seconds for container to start ===')
time.sleep(20)

# Check container status
print('=== Checking container status ===')
result = exec_cmd('docker ps --filter name=website --format "{{.Names}} {{.Status}}"')
print(result)

# Test local response
print('=== Testing local HTTP response ===')
result = exec_cmd('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/')
print(f'HTTP Status: {result}')

# Test video endpoint (NAS mount)
print('=== Testing video endpoint (NAS mount) ===')
result = exec_cmd('curl -s -o /dev/null -w "%{http_code}" "http://localhost:3000/assets/mushroom1/close%201.mp4"')
print(f'Video HTTP Status: {result}')

# Test MINDEX page
print('=== Testing MINDEX page ===')
result = exec_cmd('curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/mindex')
print(f'MINDEX HTTP Status: {result}')

print('\n=== DEPLOYMENT COMPLETE ===')
print('Please purge Cloudflare cache manually')
print('URL: https://dash.cloudflare.com -> mycosoft.com -> Caching -> Purge Everything')
