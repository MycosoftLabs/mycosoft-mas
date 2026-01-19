#!/usr/bin/env python3
"""Rebuild ONLY the website container (not other services) with latest code."""
import paramiko
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'
WEBSITE_PATH = '/opt/mycosoft/website'

def run(ssh, cmd, name, timeout=300):
    print(f"\n>>> {name}")
    print(f"    CMD: {cmd[:80]}...")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    # Only show last 50 lines of output
    lines = out.strip().split('\n')
    if len(lines) > 50:
        print(f"    ... ({len(lines) - 50} lines omitted) ...")
        print('\n'.join(lines[-50:]))
    else:
        print(out)
    if err and 'warning' not in err.lower():
        print(f"    STDERR: {err[-300:]}")
    return exit_code, out

def main():
    print('=' * 60)
    print('  REBUILDING WEBSITE ONLY (Skip other services)')
    print('=' * 60)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f'\nConnecting to {VM_HOST}...')
    ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
    print('Connected!')
    
    # 1. Pull latest code
    run(ssh, f'cd {WEBSITE_PATH} && git fetch origin && git reset --hard origin/main && git log --oneline -3', 'Pull latest code')
    
    # 2. Stop old container
    run(ssh, 'docker stop mycosoft-website 2>/dev/null || true', 'Stop old container')
    run(ssh, 'docker rm mycosoft-website 2>/dev/null || true', 'Remove old container')
    
    # 3. Build using Dockerfile.production (not docker-compose which tries to build everything)
    print("\n>>> Building with Dockerfile.production (this takes 5-10 min)...")
    exit_code, out = run(ssh, f'''
        cd {WEBSITE_PATH} && \\
        docker build -f Dockerfile.production -t website-website:latest --no-cache . 2>&1
    ''', 'Docker build', timeout=900)
    
    if exit_code != 0:
        print("\n!!! BUILD FAILED !!!")
        print("Trying with Dockerfile instead...")
        exit_code, out = run(ssh, f'''
            cd {WEBSITE_PATH} && \\
            docker build -f Dockerfile -t website-website:latest --no-cache . 2>&1
        ''', 'Docker build (alternative)', timeout=900)
        
        if exit_code != 0:
            print("\n!!! BOTH BUILDS FAILED !!!")
            ssh.close()
            return 1
    
    # 4. Start new container directly (not via compose)
    run(ssh, '''
        docker run -d \\
            --name mycosoft-website \\
            -p 3000:3000 \\
            --restart unless-stopped \\
            -e NODE_ENV=production \\
            -e PORT=3000 \\
            website-website:latest
    ''', 'Start new container')
    
    # 5. Wait and check
    print("\n>>> Waiting 20 seconds for startup...")
    time.sleep(20)
    
    run(ssh, 'docker ps --filter name=website --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"', 'Container status')
    run(ssh, 'docker logs mycosoft-website --tail 15 2>&1 || true', 'Container logs')
    
    # 6. Test endpoints
    run(ssh, 'curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:3000/', 'Test /')
    run(ssh, 'curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:3000/devices/mushroom-1', 'Test /devices/mushroom-1')
    
    # 7. Check for $2000 in the mushroom page
    exit_code, out = run(ssh, 'curl -s http://localhost:3000/devices/mushroom-1 | grep -o "\\$2,000\\|\\$2000" | head -1', 'Check for $2000 pricing')
    if '$2' in out:
        print("\n✅ NEW PRICING ($2,000) CONFIRMED!")
    else:
        print("\n❌ Old pricing still showing - changes not deployed")
    
    ssh.close()
    
    print('\n' + '=' * 60)
    print('  DONE!')
    print('=' * 60)
    print('\nVerify at: https://sandbox.mycosoft.com/devices/mushroom-1')
    return 0

if __name__ == '__main__':
    sys.exit(main())
