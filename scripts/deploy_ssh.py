"""
Direct SSH deployment to VM - bypasses Proxmox API
"""
import paramiko
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

print('=' * 60)
print('  WEBSITE DEPLOYMENT VIA SSH')
print('=' * 60)
print(f'Connecting to {VM_HOST}...')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)
except Exception as e:
    print(f'Connection failed: {e}')
    sys.exit(1)

print('Connected!\n')

def run_cmd(cmd, timeout=300, show_full=False):
    """Execute command and return output"""
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if show_full:
        print(out)
        if err:
            print(f'STDERR: {err}')
    else:
        # Show last 40 lines
        lines = out.strip().split('\n')
        print('\n'.join(lines[-40:]))
    return exit_code, out

print('[1] Pulling latest code from GitHub...')
exit_code, out = run_cmd('cd /opt/mycosoft/website && git fetch origin && git reset --hard origin/main 2>&1', show_full=True)
if exit_code != 0:
    print(f'Git pull failed with exit code {exit_code}')

print('\n[2] Current Docker images:')
run_cmd('docker images | grep website', show_full=True)

print('\n[3] Building new image (this takes 5-10 minutes)...')
build_cmd = f'cd /opt/mycosoft/website && echo "{VM_PASS}" | sudo -S docker build -t website-website:latest --no-cache . 2>&1'
exit_code, out = run_cmd(build_cmd, timeout=900)
print(f'\nBuild exit code: {exit_code}')

if exit_code != 0:
    print('\n!!! BUILD FAILED !!!')
    ssh.close()
    sys.exit(1)

print('\n[4] Stopping old container...')
run_cmd(f'echo "{VM_PASS}" | sudo -S docker stop mycosoft-website 2>/dev/null || true', show_full=True)
run_cmd(f'echo "{VM_PASS}" | sudo -S docker rm mycosoft-website 2>/dev/null || true', show_full=True)

print('\n[5] Starting new container...')
run_cmd(f'cd /opt/mycosoft && echo "{VM_PASS}" | sudo -S docker compose -p mycosoft-production up -d mycosoft-website 2>&1', show_full=True)

print('\n[6] Waiting for startup (20 seconds)...')
time.sleep(20)

print('\n[7] Container status:')
run_cmd('docker ps --filter name=mycosoft-website --format "{{.Names}}: {{.Status}}"', show_full=True)

print('\n[8] New image timestamp:')
run_cmd('docker images | grep website', show_full=True)

print('\n[9] Test health endpoint:')
run_cmd('curl -s http://localhost:3000 2>&1 | head -c 200', show_full=True)

ssh.close()

print('\n' + '=' * 60)
print('  DEPLOYMENT COMPLETE!')
print('=' * 60)
print('\nNext steps:')
print('1. Clear Cloudflare cache (PURGE EVERYTHING)')
print('2. Test: https://sandbox.mycosoft.com/login?redirectTo=%2Fdashboard%2Fcrep')
print('3. Verify OAuth buttons redirect correctly')
