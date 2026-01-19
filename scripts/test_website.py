#!/usr/bin/env python3
"""Test website endpoints."""
import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def run(client, cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode('utf-8', errors='replace')

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("Connecting to VM...")
    client.connect('192.168.0.187', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=30)
    print("Connected!\n")
    
    # Check container status
    print("Container Status:")
    print(run(client, 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep website'))
    
    # Test endpoints
    endpoints = [
        '/',
        '/devices/mushroom-1',
        '/login',
        '/dashboard',
    ]
    
    print("\nEndpoint Tests:")
    print("-" * 50)
    for endpoint in endpoints:
        status = run(client, f'curl -s -o /dev/null -w "%{{http_code}}" http://localhost:3000{endpoint}').strip()
        print(f"  {endpoint:30} -> HTTP {status}")
    
    # Get page title of mushroom-1
    print("\n\nMushroom-1 Page Content Check:")
    print("-" * 50)
    content = run(client, 'curl -s http://localhost:3000/devices/mushroom-1 | head -100')
    if 'mushroom' in content.lower() or 'Mushroom' in content:
        print("  ✓ Page contains 'mushroom' content")
    else:
        print("  ✗ Page might not have mushroom content")
        print(f"  First 200 chars: {content[:200]}")
    
    client.close()
    print("\nDone!")

if __name__ == "__main__":
    main()
