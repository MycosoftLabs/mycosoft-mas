#!/usr/bin/env python3
"""Check Proxmox status at new IP and list VMs."""

import requests
import urllib3
urllib3.disable_warnings()

# Proxmox credentials
PROXMOX_HOST = '192.168.0.90'
PROXMOX_USER = 'root@pam'
PROXMOX_PASS = '20202020'

# Alternative credentials to try
ALT_USERS = ['root@pam', 'root', 'admin@pam']
ALT_PASSES = ['20202020', 'REDACTED_VM_SSH_PASSWORD', 'admin']

def main():
    print('=== PROXMOX AUTHENTICATION ===')
    try:
        r = requests.post(
            f'https://{PROXMOX_HOST}:8006/api2/json/access/ticket',
            data={'username': PROXMOX_USER, 'password': PROXMOX_PASS},
            verify=False, timeout=10
        )
        print(f'Auth Status: {r.status_code}')
        if r.status_code == 200:
            data = r.json()['data']
            ticket = data['ticket']
            csrf = data['CSRFPreventionToken']
            print('Auth: SUCCESS')
            
            # Get nodes
            cookies = {'PVEAuthCookie': ticket}
            headers = {'CSRFPreventionToken': csrf}
            
            r2 = requests.get(
                f'https://{PROXMOX_HOST}:8006/api2/json/nodes',
                cookies=cookies, headers=headers, verify=False, timeout=10
            )
            print(f'\n=== PROXMOX NODES ===')
            for node in r2.json().get('data', []):
                print(f"Node: {node.get('node')} - Status: {node.get('status')}")
                
                # Get VMs for this node
                node_name = node.get('node')
                r3 = requests.get(
                    f'https://{PROXMOX_HOST}:8006/api2/json/nodes/{node_name}/qemu',
                    cookies=cookies, headers=headers, verify=False, timeout=10
                )
                print(f'\n=== VMs on {node_name} ===')
                for vm in r3.json().get('data', []):
                    print(f"  VM {vm.get('vmid')}: {vm.get('name')} - Status: {vm.get('status')}")
                    
                    # Get network config if running
                    if vm.get('status') == 'running':
                        vmid = vm.get('vmid')
                        try:
                            r4 = requests.get(
                                f'https://{PROXMOX_HOST}:8006/api2/json/nodes/{node_name}/qemu/{vmid}/agent/network-get-interfaces',
                                cookies=cookies, headers=headers, verify=False, timeout=10
                            )
                            if r4.status_code == 200:
                                ifaces = r4.json().get('data', {}).get('result', [])
                                for iface in ifaces:
                                    for addr in iface.get('ip-addresses', []):
                                        if addr.get('ip-address-type') == 'ipv4':
                                            print(f"    -> IP: {addr.get('ip-address')}")
                        except:
                            pass
                    
        else:
            print(f'Auth failed: {r.text}')
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    main()
