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
print("VERIFYING AUTH FIX")
print("=" * 70)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

# Wait for container to be healthy
print("\n[1] Waiting for container to be ready...")
for i in range(30):
    output, exit_code = run(ssh, "docker ps --filter name=mycosoft-website --format '{{.Status}}'")
    if 'Up' in output and 'healthy' in output:
        print("✓ Container is healthy")
        break
    elif 'Up' in output:
        print(f"Container is up, waiting for health check... ({i+1}/30)")
        time.sleep(5)
    else:
        print(f"Waiting for container to start... ({i+1}/30)")
        time.sleep(5)

# Test redirect
print("\n[2] Testing redirect from /dashboard/crep...")
output, _ = run(ssh, "curl -s -I -H 'Cookie: ' 'http://localhost:3000/dashboard/crep' | grep -i location")
print(f"Redirect header: {output.strip()}")

# Test full redirect with follow
print("\n[3] Testing full redirect chain...")
output, _ = run(ssh, "curl -s -L -o /dev/null -w '%{url_effective}' -H 'Cookie: ' 'http://localhost:3000/dashboard/crep'")
print(f"Final URL: {output.strip()}")

# Test /login directly
print("\n[4] Testing /login page directly...")
output, _ = run(ssh, "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/login")
print(f"HTTP Status: {output.strip()}")

print("\n" + "=" * 70)
if '/login' in output:
    print("✓ AUTH FIX VERIFIED - Redirects to /login (correct)")
else:
    print("⚠️  AUTH FIX NOT WORKING - Still redirecting to /auth/login")
    print("\nAction required:")
    print("1. Check Cloudflare cache (purge everything)")
    print("2. Check browser cache (hard refresh: Ctrl+Shift+R)")
    print("3. Verify middleware was rebuilt in container")

ssh.close()
