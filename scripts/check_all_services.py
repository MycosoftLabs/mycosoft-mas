#!/usr/bin/env python3
"""Check all services on VM 103 including MINDEX, NatureOS, and MycoBrain."""

import paramiko

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("Connecting to VM 103...")
    ssh.connect('192.168.0.187', username='mycosoft', password='Mushroom1!Mushroom1!')
    print("Connected!\n")
    
    # Check all running containers
    print("=" * 60)
    print("RUNNING CONTAINERS")
    print("=" * 60)
    stdin, stdout, stderr = ssh.exec_command('docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"')
    print(stdout.read().decode())
    
    # Check all containers (including stopped)
    print("=" * 60)
    print("ALL CONTAINERS (including stopped)")
    print("=" * 60)
    stdin, stdout, stderr = ssh.exec_command('docker ps -a --format "table {{.Names}}\t{{.Status}}"')
    print(stdout.read().decode())
    
    # Check all images
    print("=" * 60)
    print("DOCKER IMAGES")
    print("=" * 60)
    stdin, stdout, stderr = ssh.exec_command('docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"')
    print(stdout.read().decode())
    
    # Test local endpoints
    print("=" * 60)
    print("TESTING LOCAL ENDPOINTS")
    print("=" * 60)
    endpoints = [
        ('Website (3000)', 'http://localhost:3000'),
        ('MINDEX API (8000)', 'http://localhost:8000'),
        ('MycoBrain (8003)', 'http://localhost:8003'),
        ('NatureOS (8001)', 'http://localhost:8001'),
        ('n8n (5678)', 'http://localhost:5678'),
        ('Grafana (3001)', 'http://localhost:3001'),
    ]
    
    for name, url in endpoints:
        stdin, stdout, stderr = ssh.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" --max-time 3 {url} 2>/dev/null || echo "FAIL"')
        result = stdout.read().decode().strip()
        status = "OK" if result in ['200', '301', '302', '304'] else f"Status: {result}"
        print(f"  {name}: {status}")
    
    # Check docker networks
    print("\n" + "=" * 60)
    print("DOCKER NETWORKS")
    print("=" * 60)
    stdin, stdout, stderr = ssh.exec_command('docker network ls --format "table {{.Name}}\t{{.Driver}}"')
    print(stdout.read().decode())
    
    # Check cloudflared status
    print("=" * 60)
    print("CLOUDFLARED STATUS")
    print("=" * 60)
    stdin, stdout, stderr = ssh.exec_command('sudo systemctl status cloudflared --no-pager -l 2>&1 | head -20')
    stdin.write('Mushroom1!Mushroom1!\n')
    stdin.flush()
    print(stdout.read().decode())
    
    ssh.close()
    print("\nDone!")

if __name__ == "__main__":
    main()
