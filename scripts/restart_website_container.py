import paramiko
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'Mushroom1!Mushroom1!'

def run(ssh, cmd, timeout=300):
    print(f'\n> {cmd[:80]}...' if len(cmd) > 80 else f'\n> {cmd}')
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    exit_code = out.channel.recv_exit_status()
    output = out.read().decode('utf-8', errors='replace')
    if output.strip():
        print(output.strip()[:2000])
    return output, exit_code

print("=" * 70)
print("RESTARTING WEBSITE CONTAINER")
print("=" * 70)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print("\n[1] Checking all containers:")
run(ssh, "docker ps -a | grep website || docker ps -a | grep mycosoft")

print("\n[2] Checking Docker images:")
run(ssh, "docker images | grep website | head -3")

print("\n[3] Starting website container:")
run(ssh, f"cd /opt/mycosoft && echo '{VM_PASS}' | sudo -S docker compose -p mycosoft-production up -d mycosoft-website")

time.sleep(10)

print("\n[4] Container status:")
run(ssh, "docker ps | grep website || docker ps | grep mycosoft")

print("\n[5] Testing website:")
output, _ = run(ssh, "curl -s -o /dev/null -w '%{http_code}' --max-time 10 http://localhost:3000 || echo 'FAILED'")
print(f"HTTP Status: {output.strip()}")

print("\n[6] Container logs (last 20 lines):")
run(ssh, "docker logs $(docker ps -q --filter 'name=website' | head -1) --tail 20 2>&1 || docker ps -q | head -1 | xargs docker logs --tail 20 2>&1 | tail -20")

ssh.close()

print("\n" + "=" * 70)
print("DONE!")
print("=" * 70)
