import paramiko
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

VM_HOST = '192.168.0.187'
VM_USER = 'mycosoft'
VM_PASS = 'REDACTED_VM_SSH_PASSWORD'

def run(ssh, cmd, timeout=300):
    print(f'\n> {cmd[:80]}...' if len(cmd) > 80 else f'\n> {cmd}')
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    exit_code = out.channel.recv_exit_status()
    output = out.read().decode('utf-8', errors='replace')
    if output.strip():
        print(output.strip()[:2000])
    return output, exit_code

print("=" * 70)
print("CHECKING CONTAINER STATUS")
print("=" * 70)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

print("\n[1] Container status:")
run(ssh, "docker ps -a | grep mycosoft-website")

print("\n[2] Recent container logs (last 30 lines):")
run(ssh, "docker logs mycosoft-website --tail 30 2>&1")

print("\n[3] Checking if port 3000 is listening:")
run(ssh, "netstat -tlnp 2>/dev/null | grep :3000 || ss -tlnp | grep :3000 || echo 'Not listening'")

print("\n[4] Testing localhost:3000:")
output, exit_code = run(ssh, "curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://localhost:3000 || echo 'FAILED'")

if exit_code != 0 or '000' in output or 'FAILED' in output:
    print("\n[5] Container seems down - attempting restart...")
    run(ssh, f"cd /opt/mycosoft && echo '{VM_PASS}' | sudo -S docker compose -p mycosoft-production restart mycosoft-website")
    time.sleep(10)
    print("\n[6] Container status after restart:")
    run(ssh, "docker ps | grep mycosoft-website")
    print("\n[7] Testing again:")
    output, _ = run(ssh, "curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://localhost:3000 || echo 'FAILED'")

ssh.close()
