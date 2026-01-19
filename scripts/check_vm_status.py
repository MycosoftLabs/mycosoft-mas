#!/usr/bin/env python3
"""Check VM status and fix deployment."""
import paramiko

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("Connecting to VM 192.168.0.187...")
    client.connect('192.168.0.187', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=30)
    print("Connected!\n")
    
    # Check website directory and docker
    cmds = [
        ('Check home directory', 'ls -la /home/mycosoft/'),
        ('Check docker containers', 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"'),
        ('Check website images', 'docker images | grep -i website || echo "No website images found"'),
        ('Check mycosoft-production dir', 'ls -la /home/mycosoft/mycosoft-production/ 2>/dev/null || echo "Dir not found"'),
        ('Check docker-compose files', 'find /home/mycosoft -name "docker-compose*.yml" 2>/dev/null | head -10'),
        ('Check git repos', 'find /home/mycosoft -name ".git" -type d 2>/dev/null | head -10'),
    ]
    
    for name, cmd in cmds:
        print(f"\n{'='*60}")
        print(f">>> {name}")
        print(f">>> {cmd}")
        print('='*60)
        stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        output = stdout.read().decode()
        errors = stderr.read().decode()
        print(output)
        if errors:
            print(f"STDERR: {errors}")
    
    client.close()
    print("\n\nDone!")

if __name__ == "__main__":
    main()
