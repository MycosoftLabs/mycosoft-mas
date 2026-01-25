#!/usr/bin/env python3
"""Clear VM cache and restart website container."""

import requests
import urllib3
import time
urllib3.disable_warnings()

PROXMOX_HOST = '192.168.1.100'
PROXMOX_USER = 'root@pam'
PROXMOX_PASS = 'Mycosoft1!'
NODE = 'pve'
VMID = 103

def get_proxmox_auth():
    r = requests.post(
        f'https://{PROXMOX_HOST}:8006/api2/json/access/ticket',
        data={'username': PROXMOX_USER, 'password': PROXMOX_PASS},
        verify=False
    )
    data = r.json()['data']
    return {
        'cookies': {'PVEAuthCookie': data['ticket']},
        'headers': {'CSRFPreventionToken': data['CSRFPreventionToken']}
    }

def run_command(auth, cmd):
    print(f"Running: {cmd[:70]}...")
    r = requests.post(
        f'https://{PROXMOX_HOST}:8006/api2/json/nodes/{NODE}/qemu/{VMID}/agent/exec',
        cookies=auth['cookies'],
        headers=auth['headers'],
        verify=False,
        json={'command': 'bash', 'input-data': cmd}
    )
    if r.status_code == 200:
        pid = r.json().get('data', {}).get('pid')
        print(f"  Started (pid: {pid})")
        time.sleep(2)
        return True
    else:
        print(f"  Error: {r.status_code}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("  CLEARING VM CACHE AND RESTARTING CONTAINER")
    print("=" * 60)
    
    auth = get_proxmox_auth()
    print("[+] Authenticated to Proxmox")
    
    # Clear Linux page cache
    run_command(auth, 'sync && echo 3 > /proc/sys/vm/drop_caches')
    
    # Clear Next.js cache inside container
    run_command(auth, 'docker exec mycosoft-website rm -rf /app/.next/cache 2>/dev/null; echo done')
    
    # Restart the container
    run_command(auth, 'docker restart mycosoft-website')
    
    print("\n[*] Waiting 15 seconds for container to restart...")
    time.sleep(15)
    
    # Verify container is running
    run_command(auth, 'docker ps --filter name=mycosoft-website --format "{{.Status}}"')
    
    print("\n" + "=" * 60)
    print("  CACHE CLEARED - CONTAINER RESTARTED")
    print("=" * 60)
