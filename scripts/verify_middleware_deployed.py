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
print("VERIFYING MIDDLEWARE DEPLOYMENT")
print("=" * 70)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(VM_HOST, username=VM_USER, password=VM_PASS, timeout=30)

# Check source file
print("\n[1] Source middleware (should redirect to /login):")
run(ssh, "grep -A 2 'if (!user && isProtectedRoute)' /opt/mycosoft/website/lib/supabase/middleware.ts | grep pathname")

# Check if /app/lib/supabase/middleware.ts exists in container
print("\n[2] Checking if middleware file exists in container:")
run(ssh, "docker exec mycosoft-website test -f /app/lib/supabase/middleware.ts && echo 'EXISTS' || echo 'NOT FOUND'")

# Read the actual middleware from container
print("\n[3] Middleware in container (lines 73-77):")
run(ssh, "docker exec mycosoft-website sed -n '73,77p' /app/lib/supabase/middleware.ts 2>/dev/null || echo 'FILE NOT FOUND'")

# Check .next/server for compiled middleware
print("\n[4] Checking compiled middleware in .next/server:")
run(ssh, "docker exec mycosoft-website find /app/.next/server -name '*middleware*' -type f 2>/dev/null | head -3")

# Test actual redirect from browser perspective
print("\n[5] Testing actual redirect (simulating browser):")
run(ssh, "curl -s -I -H 'Cookie: ' 'http://localhost:3000/dashboard/crep' | grep -i location")

# Check if /login route exists
print("\n[6] Checking if /login page exists in container:")
run(ssh, "docker exec mycosoft-website test -f /app/app/login/page.tsx && echo 'EXISTS' || echo 'NOT FOUND'")

# Check if /auth/login route exists (should not)
print("\n[7] Checking if /auth/login route exists (should NOT):")
run(ssh, "docker exec mycosoft-website test -d /app/app/auth/login && echo 'EXISTS (THIS IS WRONG!)' || echo 'NOT FOUND (CORRECT)'")

ssh.close()

print("\n" + "=" * 70)
print("If middleware shows /auth/login, rebuild is needed!")
print("=" * 70)
