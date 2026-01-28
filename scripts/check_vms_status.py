#!/usr/bin/env python3
"""Check VM status and Docker containers."""

import paramiko

vms = [
    ('192.168.0.187', 'mycosoft', 'Mushroom1!Mushroom1!', 'Sandbox VM'),
    ('192.168.0.188', 'mycosoft', 'Mushroom1!Mushroom1!', 'MAS VM'),
]

print("=" * 70)
print("  VM STATUS CHECK")
print("=" * 70)

for ip, user, password, name in vms:
    print(f"\n{name} ({ip}):")
    print("-" * 50)
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(ip, username=user, password=password, timeout=10)
        print(f"  SSH: SUCCESS")
        
        # Check hostname
        stdin, stdout, stderr = client.exec_command('hostname')
        hostname = stdout.read().decode().strip()
        print(f"  Hostname: {hostname}")
        
        # Check uptime
        stdin, stdout, stderr = client.exec_command('uptime')
        uptime = stdout.read().decode().strip()
        print(f"  Uptime: {uptime}")
        
        # Check Docker
        stdin, stdout, stderr = client.exec_command('docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"')
        docker_output = stdout.read().decode().strip()
        docker_err = stderr.read().decode().strip()
        
        if docker_output:
            print(f"  Docker containers:")
            for line in docker_output.split('\n'):
                print(f"    {line}")
        elif docker_err:
            print(f"  Docker error: {docker_err[:100]}")
        else:
            print(f"  Docker: No containers running")
        
        # Check disk space
        stdin, stdout, stderr = client.exec_command('df -h / | tail -1')
        disk = stdout.read().decode().strip()
        print(f"  Disk: {disk}")
        
        # Check memory
        stdin, stdout, stderr = client.exec_command('free -h | grep Mem')
        mem = stdout.read().decode().strip()
        print(f"  Memory: {mem}")
        
        client.close()
        
    except paramiko.AuthenticationException:
        print(f"  SSH: AUTH FAILED")
    except Exception as e:
        print(f"  SSH: ERROR - {str(e)[:50]}")

print("\n" + "=" * 70)
print("  Checking Proxmox hosts...")
print("=" * 70)

proxmox_hosts = [
    ('192.168.0.202', 'root', '20202020', 'Proxmox Main'),
    ('192.168.0.90', 'root', '20202020', 'Proxmox Secondary'),
]

for ip, user, password, name in proxmox_hosts:
    print(f"\n{name} ({ip}):")
    print("-" * 50)
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(ip, username=user, password=password, timeout=10)
        print(f"  SSH: SUCCESS")
        
        # Check VMs
        stdin, stdout, stderr = client.exec_command('qm list')
        qm_output = stdout.read().decode().strip()
        print(f"  VMs:")
        for line in qm_output.split('\n'):
            print(f"    {line}")
        
        client.close()
        
    except paramiko.AuthenticationException:
        print(f"  SSH: AUTH FAILED")
    except Exception as e:
        print(f"  SSH: ERROR - {str(e)[:50]}")

print("\n" + "=" * 70)
