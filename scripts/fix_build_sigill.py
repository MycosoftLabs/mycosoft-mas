#!/usr/bin/env python3
"""Fix SIGILL build error by adjusting build settings."""
import paramiko
import time

def run_cmd(client, cmd, name, timeout=120):
    print(f"\n>>> {name}")
    print(f"    {cmd[:100]}...")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    output = stdout.read().decode()
    errors = stderr.read().decode()
    if output:
        print(output[-2000:] if len(output) > 2000 else output)
    if errors:
        print(f"STDERR: {errors[-500:]}")
    return exit_code, output

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("="*60)
    print("FIXING BUILD - SIGILL WORKAROUND")
    print("="*60)
    print("\nConnecting to VM...")
    client.connect('192.168.0.187', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=30)
    print("Connected!")
    
    # Check where the website code is
    run_cmd(client, 'ls -la /opt/mycosoft/website/ 2>/dev/null || echo "Not in /opt"', 'Check /opt path')
    
    # Find the actual path
    exit_code, output = run_cmd(client, 'find /home/mycosoft -name "package.json" -path "*website*" 2>/dev/null | head -3', 'Find website package.json')
    
    website_path = None
    for line in output.strip().split('\n'):
        if 'website' in line and 'package.json' in line:
            website_path = line.replace('/package.json', '')
            break
    
    if not website_path:
        website_path = '/home/mycosoft/mycosoft/website'
    
    print(f"\nUsing website path: {website_path}")
    
    # Try building with memory limits and NODE_OPTIONS
    # The SIGILL is often from lightningcss or other native modules
    # We can try setting NODE_OPTIONS to disable certain optimizations
    
    print("\n" + "="*60)
    print("Attempting build with SIGILL workaround...")
    print("="*60)
    
    build_cmd = f'''
cd {website_path} && \\
export NODE_OPTIONS="--max-old-space-size=8192" && \\
docker build \\
  --build-arg NODE_OPTIONS="--max-old-space-size=8192" \\
  --platform linux/amd64 \\
  -t website-website:latest \\
  --progress=plain \\
  . 2>&1
'''
    
    exit_code, output = run_cmd(client, build_cmd, 'Docker build with workaround', timeout=600)
    
    if exit_code != 0:
        print("\nBuild still failing. Let's try using the existing image...")
        
        # Check if we can just restart with existing image
        run_cmd(client, 'docker images | grep website', 'Check existing images')
        
        # Try just restarting the container
        run_cmd(client, 'docker restart mycosoft-website', 'Restart container')
        
        time.sleep(5)
        
        run_cmd(client, 'docker ps | grep website', 'Check container status')
        run_cmd(client, 'docker logs mycosoft-website --tail 30', 'Container logs')
    else:
        print("\nBuild succeeded! Restarting container...")
        run_cmd(client, 'docker stop mycosoft-website 2>/dev/null; docker rm mycosoft-website 2>/dev/null', 'Remove old container')
        run_cmd(client, f'cd {website_path} && docker compose up -d', 'Start new container')
        time.sleep(10)
        run_cmd(client, 'docker ps | grep website', 'Check new container')
    
    client.close()
    print("\n" + "="*60)
    print("DONE")
    print("="*60)

if __name__ == "__main__":
    main()
