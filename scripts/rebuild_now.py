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

print('=== STARTING DOCKER BUILD IN BACKGROUND ON VM ===')

# Start the build in background on the VM
cmd = f'''cd /opt/mycosoft/website && \\
  nohup docker build -t website-website:latest . > /tmp/docker_build.log 2>&1 &
  echo "Build started in background"
'''

_, out, _ = ssh.exec_command(cmd)
print(out.read().decode('utf-8', errors='replace'))

print('\n[1] Checking build progress (waiting 10 seconds)...')
time.sleep(10)

_, out, _ = ssh.exec_command('tail -20 /tmp/docker_build.log 2>&1')
print(out.read().decode('utf-8', errors='replace'))

print('\n[2] Is docker build still running?')
_, out, _ = ssh.exec_command('ps aux | grep "docker build" | grep -v grep')
result = out.read().decode('utf-8', errors='replace')
if result:
    print('Build is running...')
    print(result)
else:
    print('Build may have finished or not started')

ssh.close()
print('\nRun this script again to check progress, or check /tmp/docker_build.log on the VM')
