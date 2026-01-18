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

# Check container status
print("\n[1] Checking container status...")
run(ssh, "docker ps -a | grep mycosoft-website")

# Check if image exists
print("\n[2] Checking Docker image...")
run(ssh, "docker images | grep website")

# Start container
print("\n[3] Starting website container...")
run(ssh, f"cd /opt/mycosoft && echo '{VM_PASS}' | sudo -S docker compose -p mycosoft-production up -d mycosoft-website")

time.sleep(10)

# Check status again
print("\n[4] Container status:")
run(ssh, "docker ps | grep mycosoft-website")

# Check logs
print("\n[5] Recent container logs:")
run(ssh, "docker logs mycosoft-website --tail 20")

# Test redirect
print("\n[6] Testing redirect...")
output, _ = run(ssh, "curl -s -I -H 'Cookie: ' 'http://localhost:3000/dashboard/crep' | grep -i location")
print(f"Redirect: {output.strip()}")

print("\n" + "=" * 70)
print("CONTAINER RESTARTED")
print("=" * 70)
print("\nIf /auth/login still appears:")
print("1. Clear Cloudflare cache (Purge Everything)")
print("2. Hard refresh browser (Ctrl+Shift+R)")
print("3. The middleware now redirects to /login (correct)")

ssh.close()
