import paramiko
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

def run(cmd):
    print(f'$ {cmd}')
    _, out, err = ssh.exec_command(cmd, timeout=60)
    out.channel.recv_exit_status()
    output = out.read().decode('utf-8', errors='replace')
    if output.strip():
        print(output.strip())
    return output

print('=== FIXING CONTAINER CONFLICT ===\n')

print('[1] Stop all website containers:')
run(f'echo "{VM_PASS}" | sudo -S docker stop $(docker ps -aq --filter name=website) 2>/dev/null')

print('\n[2] Remove all website containers:')
run(f'echo "{VM_PASS}" | sudo -S docker rm $(docker ps -aq --filter name=website) 2>/dev/null')

print('\n[3] Remove any conflicting containers:')
run(f'echo "{VM_PASS}" | sudo -S docker rm -f 810fa8e356c9 7cdaf38786f8 2>/dev/null')

print('\n[4] Start fresh:')
run(f'cd /opt/mycosoft && echo "{VM_PASS}" | sudo -S docker compose -p mycosoft-production up -d mycosoft-website 2>&1')

print('\n[5] Wait 30 seconds...')
time.sleep(30)

print('\n[6] Container status:')
run('docker ps --filter name=mycosoft-website')

print('\n[7] Test Supabase URL in page source:')
output = run("curl -s http://localhost:3000/login | grep -o 'https://[a-z]*\\.supabase\\.co' | head -1")
if 'kzwnthsxofkkdxcmqbcl' in output:
    print('\n*** REAL Supabase URL confirmed! ***')
elif 'placeholder' in output:
    print('\n*** ERROR: Still using placeholder! ***')

print('\n[8] OAuth buttons:')
run("curl -s http://localhost:3000/login | grep -io 'continue with google\\|continue with github'")

print('\n=== DONE - Clear Cloudflare cache! ===')

ssh.close()
