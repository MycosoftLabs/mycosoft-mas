#!/usr/bin/env python3
"""Check MAS Earth-2 deployment status."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.188', username='mycosoft', password='Mushroom1!Mushroom1!', timeout=10)

print('=== Container logs (last 30 lines) ===')
stdin, stdout, stderr = ssh.exec_command('docker logs myca-orchestrator-new --tail 30 2>&1', timeout=30)
print(stdout.read().decode())

print('\n=== Checking if Earth-2 files exist ===')
stdin, stdout, stderr = ssh.exec_command('ls -la /home/mycosoft/mycosoft/mas/mycosoft_mas/core/routers/earth2_api.py 2>&1', timeout=10)
print(stdout.read().decode())

print('\n=== Checking Earth-2 module in container ===')
cmd = 'docker exec myca-orchestrator-new ls -la /app/mycosoft_mas/core/routers/ | grep earth2'
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
out = stdout.read().decode()
err = stderr.read().decode()
print(f'OUT: {out}')
print(f'ERR: {err}')

print('\n=== Try importing Earth-2 in container ===')
cmd = 'docker exec myca-orchestrator-new python3 -c "from mycosoft_mas.core.routers import earth2_api; print(earth2_api)"'
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
out = stdout.read().decode()
err = stderr.read().decode()
print(f'OUT: {out}')
print(f'ERR: {err}')

print('\n=== Check EARTH2_API_AVAILABLE flag ===')
cmd = 'docker exec myca-orchestrator-new python3 -c "from mycosoft_mas.core.myca_main import EARTH2_API_AVAILABLE; print(f\'EARTH2_API_AVAILABLE={EARTH2_API_AVAILABLE}\')"'
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
out = stdout.read().decode()
err = stderr.read().decode()
print(f'OUT: {out}')
print(f'ERR: {err}')

ssh.close()
print('\nDone!')
