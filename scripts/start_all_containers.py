#!/usr/bin/env python3
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.187', username='mycosoft', password='Mushroom1!Mushroom1!')

VM_PASS = 'Mushroom1!Mushroom1!'

def run(cmd, timeout=300):
    full_cmd = f"echo '{VM_PASS}' | sudo -S {cmd}"
    print(f">>> {cmd[:60]}...")
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        for line in out.split('\n')[-10:]:
            if line.strip():
                print(f"  {line}")
    return out

print("=== Starting all containers ===")
run("docker compose -f /home/mycosoft/mycosoft/docker-compose.yml up -d", timeout=300)

print("\n=== Waiting for startup ===")
time.sleep(15)

print("\n=== Container Status ===")
run("docker ps --format 'table {{.Names}}\t{{.Status}}'")

print("\n=== Testing Services ===")
for port, name in [(3000, 'Website'), (8000, 'MINDEX'), (8001, 'MAS'), (8003, 'MycoBrain'), (5678, 'n8n'), (3002, 'Grafana'), (6333, 'Qdrant')]:
    cmd = f'curl -s -o /dev/null -w "%{{http_code}}" http://localhost:{port} 2>/dev/null || echo FAIL'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    result = stdout.read().decode().strip()
    status = 'OK' if result in ['200', '302', '401'] else result
    print(f"  {name} (:{port}): {status}")

ssh.close()
print("\nDone!")
