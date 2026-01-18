import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print('=== VERIFYING SUPABASE URL IN BUILD ===\n')

print('[1] Container env vars:')
_, out, _ = ssh.exec_command('docker exec mycosoft-website env | grep -i supabase')
print(out.read().decode('utf-8', errors='replace'))

print('[2] Check .next/server for supabase url:')
_, out, _ = ssh.exec_command("docker exec mycosoft-website sh -c \"grep -r 'supabase.co' .next/server/*.js 2>/dev/null | head -3\"")
print(out.read().decode('utf-8', errors='replace')[:500] + '...')

print('\n[3] Check static JS chunks for supabase:')
_, out, _ = ssh.exec_command("docker exec mycosoft-website sh -c \"grep -r 'kzwnth' .next/static 2>/dev/null | head -1\"")
result = out.read().decode('utf-8', errors='replace')
if 'kzwnth' in result:
    print('FOUND real Supabase URL in static chunks!')
else:
    print('Checking for placeholder...')
    _, out, _ = ssh.exec_command("docker exec mycosoft-website sh -c \"grep -r 'placeholder.supabase' .next/static 2>/dev/null | head -1\"")
    result = out.read().decode('utf-8', errors='replace')
    if 'placeholder' in result:
        print('ERROR: Still has placeholder!')
    else:
        print('Neither found - checking full page...')

print('\n[4] Full curl for auth URLs:')
_, out, _ = ssh.exec_command("curl -s http://localhost:3000/login | grep -o 'https://[^\"]*supabase[^\"]*' | head -3")
print(out.read().decode('utf-8', errors='replace'))

ssh.close()
