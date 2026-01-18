import paramiko
import sys
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
print("CHECKING AUTH REDIRECT ON VM")
print("=" * 70)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

# Check middleware file on VM
print("\n[1] Checking middleware file on VM...")
run(ssh, "grep -n 'pathname =' /opt/mycosoft/website/lib/supabase/middleware.ts | grep login")

# Check what's in the container
print("\n[2] Checking middleware in container...")
run(ssh, "docker exec mycosoft-website cat /app/lib/supabase/middleware.ts | grep -A 3 'pathname =' | grep login || echo 'NOT FOUND'")

# Test redirect by accessing protected route
print("\n[3] Testing redirect from /dashboard/crep...")
output, _ = run(ssh, "curl -s -L -o /dev/null -w '%{url_effective}' -H 'Cookie: ' http://localhost:3000/dashboard/crep")
print(f"Redirected to: {output.strip()}")

# Check if /auth/login route exists
print("\n[4] Checking if /auth/login route exists...")
run(ssh, "docker exec mycosoft-website ls -la /app/app/auth/ 2>/dev/null || echo 'No /auth directory'")

# Check for any references to /auth/login in built files
print("\n[5] Checking for /auth/login references in container...")
run(ssh, "docker exec mycosoft-website grep -r '/auth/login' /app/.next 2>/dev/null | head -3 || echo 'No /auth/login found'")

ssh.close()
