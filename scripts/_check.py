import requests, urllib3, time
urllib3.disable_warnings()

headers = {'Authorization': f'PVEAPIToken={os.environ.get("PROXMOX_TOKEN_ID", "myca@pve!mas")}={os.environ.get("PROXMOX_TOKEN_SECRET", "")}'}
PROXMOX = 'https://192.168.0.202:8006'

def exec_cmd(cmd, wait=10):
    data = {'command': '/bin/bash', 'input-data': cmd}
    r = requests.post(f'{PROXMOX}/api2/json/nodes/pve/qemu/103/agent/exec', headers=headers, data=data, verify=False, timeout=10)
    if not r.ok: return f"Error: {r.status_code}"
    pid = r.json().get('data', {}).get('pid')
    if not pid: return 'No PID'
    time.sleep(wait)
    s = requests.get(f'{PROXMOX}/api2/json/nodes/pve/qemu/103/agent/exec-status', headers=headers, params={'pid': pid}, verify=False, timeout=10)
    if s.ok:
        data = s.json().get('data', {})
        return data.get('out-data', '') if data.get('exited') else 'still running...'
    return 'status check failed'

print('=== Docker Containers ===')
print(exec_cmd('docker ps --format "{{.Names}}: {{.Status}}"', 5))

print('\n=== Restart Container ===')
print(exec_cmd('cd /home/mycosoft/mycosoft/mas && docker compose -f docker-compose.always-on.yml up -d mycosoft-website 2>&1', 30))

print('\n=== Container Status After Restart ===')
print(exec_cmd('docker ps --format "{{.Names}}: {{.Status}}" | grep website', 5))
